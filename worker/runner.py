"""Worker — entrada de execução (processo separado da UI Streamlit, R4).

FASE 1: demonstra o núcleo do projeto — abrir o Almah com a sessão persistida,
confirmar que está logado e validar a troca de condomínio (R1). Sem seletores
reais de 'nome_ativo', o passo de validação para com mensagem clara, como
projetado.

Uso:
    python -m worker.runner --condominio "NOME EXATO NO ALMAH"
"""
from __future__ import annotations
import argparse

from automation.browser import BrowserManager, SessaoInvalidaError
from automation.pages.condominio_page import CondominioPage, CondominioDivergenteError
from core.config.selectors import Selectors, SeletorIndisponivelError
from core.config.settings import settings
from core.logging.logger import get_logger

log = get_logger("worker")


def executar(nome_condominio: str) -> int:
    selectors = Selectors()
    browser = BrowserManager()

    try:
        with browser.pagina() as page:
            log.info("Abrindo Almah: %s", settings.almah_base_url)
            page.goto(settings.almah_base_url)
            page.wait_for_load_state("networkidle")

            seletor_login = selectors.chain("login.indicador_tela_login")
            if not browser.sessao_ativa(page, seletor_login):
                log.error("Sessão expirada. Rode: python -m automation.login")
                return 2

            log.info("Sessão ativa. Validando condomínio: %s", nome_condominio)
            cond = CondominioPage(page, selectors, browser)
            cond.trocar(nome_condominio)
            cond.validar_ativo(nome_condominio)

            log.info("OK — condomínio validado. (Próximos passos: Financeiro > "
                     "Contas a Pagar, recorrência, etc. — Fase 3.)")
            return 0

    except SessaoInvalidaError as e:
        log.error("%s", e)
        return 2
    except SeletorIndisponivelError as e:
        log.error("Bloqueado por seletor ausente: %s", e)
        log.error("Preencha core/config/selectors.yaml (ver itens 'TODO').")
        return 3
    except CondominioDivergenteError as e:
        log.error("PARADA DE SEGURANÇA (R1): %s", e)
        return 4


def main() -> None:
    ap = argparse.ArgumentParser(description="Worker Almah x Meka (Fase 1)")
    ap.add_argument("--condominio", required=True, help="Nome EXATO do condomínio no Almah")
    args = ap.parse_args()
    raise SystemExit(executar(args.condominio))


if __name__ == "__main__":
    main()
