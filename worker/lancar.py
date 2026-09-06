"""Executa um lancamento a partir de um JSON aprovado."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from api.services import executar_lancamento_json
from core.logging.logger import get_logger

log = get_logger("lancar")


def main() -> None:
    parser = argparse.ArgumentParser(description="Lancamento Almah")
    parser.add_argument("--arquivo", required=True)
    parser.add_argument("--condominio", required=True)
    parser.add_argument(
        "--confirmar",
        action="store_true",
        help="Salva de verdade; sem esta opcao executa somente a previa.",
    )
    args = parser.parse_args()

    dados = json.loads(Path(args.arquivo).read_text(encoding="utf-8"))
    try:
        resultado = executar_lancamento_json(
            dados,
            confirmar=True if args.confirmar else None,
            cond=args.condominio,
        )
        log.info("RESULTADO [%s]: %s", resultado.get("status", "erro"), resultado.get("mensagem") or resultado.get("erro"))
        raise SystemExit(0 if resultado.get("ok") else 5)
    except Exception:
        log.exception("Falha ao executar lancamento")
        raise SystemExit(2)


if __name__ == "__main__":
    main()
