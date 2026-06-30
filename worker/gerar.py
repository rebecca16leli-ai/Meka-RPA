"""Gera o JSON de lançamento a partir de uma pasta de PDFs (Fase 2).

Uso:
    python -m worker.gerar --pasta data/pdfs --fornecedor 0664 \
        --condominio "CONDOMINIO TESTE - RAFAEL" [--competencia 05/2026] \
        [--filtro "Bloco 04"] [--saida data/lancamento_gerado.json]

Depois, confira e lance:
    python -m worker.lancar --arquivo data/lancamento_gerado.json          (prévia)
    python -m worker.lancar --arquivo data/lancamento_gerado.json --confirmar
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from extraction.montar import montar_lancamento
from core.logging.logger import get_logger

log = get_logger("gerar")


def main() -> None:
    ap = argparse.ArgumentParser(description="Gera o JSON de lançamento a partir dos PDFs")
    ap.add_argument("--pasta", required=True, help="Pasta com os PDFs (boleto, comprovante, NF)")
    ap.add_argument("--fornecedor", required=True, help="Código do fornecedor (ex.: 0664)")
    ap.add_argument("--condominio", required=True, help="Nome exato do condomínio no Almah")
    ap.add_argument("--competencia", default=None, help="MM/AAAA (default: sugerida pela extração)")
    ap.add_argument("--filtro", default=None, help="Filtro de descrição (caso COPEL: 'Bloco 04')")
    ap.add_argument("--saida", default="data/lancamento_gerado.json")
    args = ap.parse_args()

    dados = montar_lancamento(args.pasta, args.fornecedor,
                              competencia=args.competencia, filtro_descricao=args.filtro)
    dados["condominio"] = args.condominio

    ext = dados["_extracao"]
    print("\n===================== PRÉVIA DA EXTRAÇÃO =====================")
    print(f"  Condomínio : {dados['condominio']}")
    print(f"  Fornecedor : {dados['fornecedor_nome']} ({dados['fornecedor_codigo']})")
    print(f"  Competência: {dados['competencia']}")
    print(f"  Valor      : {dados['valor_liquido']}")
    print(f"  Emissão    : {dados['emissao']}   Vencimento: {dados['vencimento']}")
    print(f"  Complemento: {dados['complemento']}")
    print(f"  Anexos     : {len(dados['anexos'])} arquivo(s)")
    print(f"  Nº NF      : {ext['numero_nf']}")
    print(f"  CONFIÁVEL  : {ext['confiavel']}   (precisa revisão: {ext['precisa_revisao']})")
    for a in ext["avisos"]:
        print(f"   - AVISO: {a}")
    print("=============================================================")

    saida = Path(args.saida)
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(json.dumps(dados, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"JSON salvo em: {saida}")
    if ext["precisa_revisao"]:
        print(">>> ATENÇÃO: extração marcada para REVISÃO. Confira antes de lançar. <<<")
    else:
        print("Tudo certo. Próximo passo: python -m worker.lancar --arquivo "
              f"{saida} (prévia) e depois --confirmar.")


if __name__ == "__main__":
    main()
