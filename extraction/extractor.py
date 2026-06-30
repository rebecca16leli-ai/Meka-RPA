"""Extração de dados dos PDFs (Fase 2).

Determinístico:
  - valor: da LINHA DIGITÁVEL do boleto (últimos 10 dígitos = centavos);
  - vencimento: do FATOR de vencimento da linha digitável (sem ambiguidade de texto);
  - emissão / nº NF: do texto da NF;
  - cruzamento: comprovante e NF devem conter o mesmo valor; senão -> REVISÃO.

A competência NÃO vem do PDF (é a escolha do operador). Sugerimos competência
= mês/ano do vencimento, mas pode ser sobrescrita.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

import pdfplumber

LD_RE = re.compile(r"\d{5}\.\d{5}\s+\d{5}\.\d{6}\s+\d{5}\.\d{6}\s+\d\s+\d{14}")
# Base do fator de vencimento após o reset de 22/02/2025 (Febraban).
BASE_FATOR = date(2025, 2, 22)


@dataclass
class ResultadoExtracao:
    valor: float | None = None
    vencimento: str | None = None       # AAAA-MM-DD
    emissao: str | None = None          # AAAA-MM-DD
    numero_nf: str | None = None
    competencia_sugerida: str | None = None
    confiavel: bool = True
    avisos: list[str] = field(default_factory=list)
    fontes: dict = field(default_factory=dict)


def ler_texto(caminho: str | Path) -> str:
    with pdfplumber.open(str(caminho)) as pdf:
        return "\n".join((p.extract_text() or "") for p in pdf.pages)


def _digitos_ld(texto: str) -> str | None:
    m = LD_RE.search(texto)
    return re.sub(r"\D", "", m.group(0)) if m else None


def valor_da_linha_digitavel(texto: str) -> float | None:
    d = _digitos_ld(texto)
    if not d:
        return None
    try:
        return int(d[-14:][4:]) / 100.0   # bloco final: fator(4) + valor(10)
    except ValueError:
        return None


def vencimento_da_linha_digitavel(texto: str) -> str | None:
    d = _digitos_ld(texto)
    if not d:
        return None
    fator = int(d[-14:][:4])
    if fator < 1000:
        return None
    venc = BASE_FATOR + timedelta(days=fator - 1000)
    return venc.isoformat()


def _datas_no_texto(texto: str) -> set[str]:
    return {f"{a}-{m}-{d}" for d, m, a in re.findall(r"\b(\d{2})/(\d{2})/(\d{4})\b", texto)}


def _data_apos_rotulo(texto: str, rotulo: str) -> str | None:
    m = re.search(rotulo + r"[^\d]{0,15}(\d{2})/(\d{2})/(\d{4})", texto, re.IGNORECASE)
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else None


def _valor_apos_rotulo(texto: str, rotulos: list[str]) -> float | None:
    for rot in rotulos:
        m = re.search(rot + r"[^\d]{0,15}(\d{1,3}(?:\.\d{3})*,\d{2})", texto, re.IGNORECASE)
        if m:
            return float(m.group(1).replace(".", "").replace(",", "."))
    return None


def _valor_br(v: float) -> str:
    return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _classificar(caminho: str, texto: str) -> str:
    nome = Path(caminho).name.lower()
    if "boleto" in nome:
        return "boleto"
    if "comprov" in nome or nome.startswith("c_") or nome.startswith("c "):
        return "comprovante"
    if nome.startswith("nf") or "nota" in nome:
        return "nf"
    up = texto.upper()
    if "COMPROVANTE DE" in up and "PAGAMENTO" in up:
        return "comprovante"
    if "DANFE" in up or "NF-E" in up:
        return "nf"
    if LD_RE.search(texto):
        return "boleto"
    return "desconhecido"


def extrair(caminhos: list[str]) -> ResultadoExtracao:
    r = ResultadoExtracao()
    textos: dict[str, str] = {}

    for c in caminhos:
        texto = ler_texto(c)
        tipo = _classificar(c, texto)
        textos[tipo] = texto
        r.fontes[tipo] = Path(c).name

    # ---- valor e vencimento: do boleto (linha digitável) ----
    boleto = textos.get("boleto", "")
    r.valor = valor_da_linha_digitavel(boleto)
    venc_ld = vencimento_da_linha_digitavel(boleto)
    # confiança extra: o vencimento do fator deve aparecer no texto do boleto
    if venc_ld and venc_ld in _datas_no_texto(boleto):
        r.vencimento = venc_ld
    else:
        r.vencimento = venc_ld or _data_apos_rotulo(textos.get("comprovante", ""), "Vencimento")

    # ---- emissão e nº NF ----
    nf = textos.get("nf", "")
    # tenta vários rótulos comuns (NF e boleto). Em boleto, 'Data do Documento'
    # e 'Data do Processamento' equivalem à emissão.
    for fonte, rotulo in [
        (nf, r"EMISS[ÃA]O"),
        (boleto, r"Data\s+do\s+Documento"),
        (boleto, r"Data\s+Documento"),
        (boleto, r"Data\s+do\s+Processamento"),
        (boleto, r"Data\s+Processamento"),
        (nf, r"Data\s+de?\s+Emiss[ãa]o"),
    ]:
        if not fonte:
            continue
        achou = _data_apos_rotulo(fonte, rotulo)
        if achou:
            r.emissao = achou
            break
    mnf = re.search(r"N[°º]\s*([\d.]{7,})", nf)
    if mnf:
        r.numero_nf = re.sub(r"\D", "", mnf.group(1))

    # ---- cruzamento de confiança ----
    if r.valor is None:
        r.confiavel = False
        r.avisos.append("Não foi possível extrair o valor do boleto.")
    else:
        alvo = _valor_br(r.valor)
        comp = textos.get("comprovante", "")
        if comp and alvo not in comp:
            r.confiavel = False
            r.avisos.append(f"Valor {alvo} não confere no comprovante.")
        if nf and alvo not in nf:
            r.confiavel = False
            r.avisos.append(f"Valor {alvo} não confere na NF.")

    if r.vencimento is None:
        r.confiavel = False
        r.avisos.append("Não foi possível extrair o vencimento.")
    else:
        a, m, _ = r.vencimento.split("-")
        r.competencia_sugerida = f"{m}/{a}"

    if r.emissao is None:
        r.confiavel = False
        r.avisos.append("Não foi possível extrair a data de emissão.")

    return r
