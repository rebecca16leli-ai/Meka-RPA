"""De-para de fornecedores (Módulo 4 / Configurações).

Resolve, para um fornecedor:
  - conta (código reduzido) a selecionar no Select2;
  - tipo de documento;
  - descrição-padrão (para montar o complemento).

Regra da conta:
  1) usa conta_padrao_reduzido de fornecedor_config.csv, se houver;
  2) senão, se o fornecedor tiver UMA única conta em fornecedor_contas.csv, usa-a;
  3) senão (várias contas, sem padrão) -> retorna None => o chamador deve mandar
     o lançamento para REVISÃO (não escolher sozinho).
"""
from __future__ import annotations
import csv
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"


@dataclass
class FornecedorResolvido:
    codigo: str
    nome_almah: str
    conta_reduzido: str | None
    tipo_documento: str | None
    descricao_padrao: str | None
    precisa_revisao: bool
    motivo: str = ""


def _ler_csv(nome: str) -> list[dict]:
    caminho = DATA / nome
    if not caminho.exists():
        return []
    with open(caminho, encoding="utf-8") as f:
        return list(csv.DictReader(f))


class DeParaFornecedores:
    def __init__(self) -> None:
        self.fornecedores = {r["codigo"]: r for r in _ler_csv("fornecedores.csv")}
        self.config = {r["codigo_fornecedor"]: r for r in _ler_csv("fornecedor_config.csv")}
        self.contas: dict[str, list[dict]] = {}
        for r in _ler_csv("fornecedor_contas.csv"):
            self.contas.setdefault(r["codigo_fornecedor"], []).append(r)

    def resolver(self, codigo: str) -> FornecedorResolvido:
        forn = self.fornecedores.get(codigo)
        nome = forn["nome_almah"] if forn else ""
        cfg = self.config.get(codigo)
        contas = self.contas.get(codigo, [])

        if cfg and cfg.get("conta_padrao_reduzido"):
            return FornecedorResolvido(
                codigo, nome, cfg["conta_padrao_reduzido"],
                cfg.get("tipo_documento"), cfg.get("descricao_padrao"),
                precisa_revisao=False,
            )
        if len(contas) == 1:
            return FornecedorResolvido(
                codigo, nome, contas[0]["conta_codigo_reduzido"],
                None, None, precisa_revisao=False,
            )
        motivo = ("sem conta cadastrada" if not contas
                  else f"{len(contas)} contas e sem padrão definido em fornecedor_config.csv")
        return FornecedorResolvido(codigo, nome, None, None, None,
                                   precisa_revisao=True, motivo=motivo)


def montar_complemento(descricao_padrao: str | None, competencia: str) -> str:
    base = (descricao_padrao or "").strip()
    return f"{base} REF. {competencia}".strip()
