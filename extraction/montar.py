"""Monta um lançamento (dict/JSON) a partir dos PDFs + de-para do fornecedor.

Junta:
  - dados extraídos dos PDFs (valor, vencimento, emissão);  -> extraction
  - conta/tipo/descrição do fornecedor;                      -> de-para
  - competência (do operador; default = sugerida pela extração).

Resultado: o mesmo formato que worker.lancar já consome.
"""
from __future__ import annotations
from pathlib import Path

from extraction.extractor import extrair
from core.domain.fornecedores import DeParaFornecedores, montar_complemento


def _pdfs_da_pasta(pasta: str | Path) -> list[str]:
    p = Path(pasta)
    return sorted(str(x) for x in p.glob("*.pdf"))


def montar_lancamento(pasta_pdfs: str, fornecedor_codigo: str,
                      competencia: str | None = None,
                      filtro_descricao: str | None = None) -> dict:
    arqs = _pdfs_da_pasta(pasta_pdfs)
    ext = extrair(arqs)

    depara = DeParaFornecedores()
    forn = depara.resolver(fornecedor_codigo)

    competencia = competencia or ext.competencia_sugerida
    # complemento será refinado no lançamento (mantém o texto-base da recorrência
    # e atualiza a referência). Aqui usamos um fallback só para a prévia.
    complemento = montar_complemento(forn.descricao_padrao, competencia) if competencia else None

    avisos = list(ext.avisos)
    # A CONTA do fornecedor NÃO é mais motivo de revisão: a automação lê a conta
    # que já está na recorrência e a mantém. Só a extração dos PDFs gera revisão.
    precisa_revisao = not ext.confiavel

    return {
        "condominio": None,  # definido pelo operador / painel
        "competencia": competencia,
        "fornecedor_codigo": fornecedor_codigo,
        "fornecedor_nome": forn.nome_almah,
        "documento_referencia": f"REF. {competencia}" if competencia else None,
        "valor_liquido": ext.valor,
        "emissao": ext.emissao,
        "vencimento": ext.vencimento,
        "prev_pagto": ext.vencimento,
        "complemento": complemento,
        "filtro_descricao": filtro_descricao,
        "anexos": arqs,
        "_extracao": {
            "confiavel": ext.confiavel,
            "precisa_revisao": precisa_revisao,
            "avisos": avisos,
            "numero_nf": ext.numero_nf,
            "fontes": ext.fontes,
        },
    }
