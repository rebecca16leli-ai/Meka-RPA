"""Executa um lançamento a partir de um JSON aprovado.

Segurança: por padrão roda em DRY-RUN (preenche tudo e PARA antes de salvar).
Só salva de verdade com --confirmar.

Uso:
    python -m worker.lancar --arquivo data/exemplo_lancamento.json
    python -m worker.lancar --arquivo data/exemplo_lancamento.json --confirmar
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from automation.browser import BrowserManager, SessaoInvalidaError
from automation.flow import executar_lancamento
from automation.pages.condominio_page import CondominioDivergenteError
from automation.pages.contas_pagar_page import (
    RecorrenciaNaoEncontradaError, RecorrenciaAmbiguaError,
)
from core.config.selectors import Selectors, SeletorIndisponivelError
from core.config.settings import settings
from core.logging.logger import get_logger

log = get_logger("lancar")


def main() -> None:
    ap = argparse.ArgumentParser(description="Lançamento Almah (dry-run por padrão)")
    ap.add_argument("--arquivo", required=True, help="JSON do lançamento aprovado")
    ap.add_argument("--confirmar", action="store_true",
                    help="SALVAR de verdade (sem isso, é só prévia/dry-run)")
    args = ap.parse_args()

    dados = json.loads(Path(args.arquivo).read_text(encoding="utf-8"))
    selectors = Selectors()
    browser = BrowserManager()
    dry_run = not args.confirmar

    log.info("Modo: %s", "DRY-RUN (não salva)" if dry_run else "CONFIRMAR (salva)")
    try:
        with browser.pagina() as page:
            page.goto(settings.almah_base_url)
            page.wait_for_load_state("networkidle")
            if not browser.esta_logado(page, selectors):
                log.error("Sessão expirada (apareceu a tela de login). Rode: python -m automation.login")
                raise SystemExit(2)

            r = executar_lancamento(page, browser, selectors, dados, dry_run=dry_run)
            log.info("RESULTADO [%s]: %s", r.status.upper(), r.mensagem)
            for e in r.evidencias:
                log.info("  evidência: %s", e)
            raise SystemExit(0 if r.ok else 5)

    except SessaoInvalidaError as e:
        log.error("%s", e); raise SystemExit(2)
    except SeletorIndisponivelError as e:
        log.error("Seletor ausente: %s", e); raise SystemExit(3)
    except CondominioDivergenteError as e:
        log.error("PARADA DE SEGURANÇA (condomínio): %s", e); raise SystemExit(4)
    except RecorrenciaAmbiguaError as e:
        log.error("REVISÃO (ambiguidade de competência): %s", e); raise SystemExit(6)
    except RecorrenciaNaoEncontradaError as e:
        log.error("Recorrência não encontrada: %s", e); raise SystemExit(7)


if __name__ == "__main__":
    main()
