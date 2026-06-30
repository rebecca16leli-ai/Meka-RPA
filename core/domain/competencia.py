"""Competência e datas (Módulo 4 — regras)."""
from __future__ import annotations
import re
from datetime import date, datetime

COMPETENCIA_RE = re.compile(r"^(0[1-9]|1[0-2])/(\d{4})$")
DATA_BR_RE = re.compile(r"\b(\d{2})/(\d{2})/(\d{4})\b")


def validar_competencia(competencia: str) -> tuple[int, int]:
    """'MM/AAAA' -> (mes, ano). Lança ValueError se inválida."""
    m = COMPETENCIA_RE.match(competencia.strip())
    if not m:
        raise ValueError(f"Competência inválida: '{competencia}' (use MM/AAAA).")
    return int(m.group(1)), int(m.group(2))


def para_data(valor) -> date:
    """Aceita date, 'AAAA-MM-DD' ou 'DD/MM/AAAA'."""
    if isinstance(valor, date):
        return valor
    s = str(valor).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Data inválida: '{valor}'")


def data_br(valor) -> str:
    """date/str -> 'DD/MM/AAAA' (formato do Almah)."""
    return para_data(valor).strftime("%d/%m/%Y")


def vencimento_casa_competencia(texto_linha: str, competencia: str) -> bool:
    """True se alguma data DD/MM/AAAA no texto da linha tem mês/ano == competência."""
    mes, ano = validar_competencia(competencia)
    for d, m, a in DATA_BR_RE.findall(texto_linha):
        if int(m) == mes and int(a) == ano:
            return True
    return False


REF_RE = re.compile(r"\s*REF\.?\s*\d{2}/\d{4}\s*$", re.IGNORECASE)


def atualizar_referencia(texto: str, competencia: str) -> str:
    """Mantém o texto-base e troca a competência no final.
    Ex.: ('REABASTECIMENTO DE GÁS REF. 05/2024', '05/2026')
         -> 'REABASTECIMENTO DE GÁS REF. 05/2026'."""
    base = REF_RE.sub("", (texto or "").strip()).strip()
    return f"{base} REF. {competencia}".strip()
