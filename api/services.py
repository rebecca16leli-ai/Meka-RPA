from __future__ import annotations

from typing import Any

from playwright.sync_api import sync_playwright

from automation.browser import BrowserManager
from automation.flow import executar_lancamento
from core.config.selectors import Selectors, SeletorIndisponivelError
from core.config.settings import settings
from core.logging.logger import get_logger

log = get_logger("api")


def iniciar_login_manual() -> str:
    settings.auth_state_file.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:

        browser = p.chromium.launch(
            executable_path=settings.chrome_path,
            headless=False,
        )

        context = browser.new_context()

        page = context.new_page()

        page.goto(settings.almah_base_url)

        page.wait_for_event(
            "close",
            timeout=0,
        )

        context.storage_state(
            path=str(settings.auth_state_file)
        )

        browser.close()

    return "Sessão gravada com sucesso."


def validar_condominio(condominio: str) -> dict[str, Any]:

    selectors = Selectors()
    browser = BrowserManager()

    with browser.pagina() as page:

        page.goto(settings.almah_base_url)

        page.wait_for_load_state("networkidle")

        seletor_login = selectors.chain("login.indicador_tela_login")

        if not browser.sessao_ativa(page, seletor_login):
            return {
                "ok": False,
                "erro": "Sessão expirada. Rode o login novamente."
            }

        try:

            from automation.pages.condominio_page import CondominioPage

            cond = CondominioPage(page, selectors, browser)

            cond.trocar(condominio)

            cond.validar_ativo(condominio)

        except SeletorIndisponivelError as e:

            return {
                "ok": False,
                "erro": str(e)
            }

        except Exception as e:

            return {
                "ok": False,
                "erro": str(e)
            }

        return {
            "ok": True,
            "mensagem": "Condomínio validado."
        }


def executar_lancamento_json( dados: str, confirmar: bool = False, cond: str = None, ) -> dict[str, Any]:
    selectors = Selectors()
    browser = BrowserManager()

    dry_run = not confirmar
    with browser.pagina() as page:
        page.goto(settings.almah_base_url)

        page.wait_for_load_state("networkidle")

        if not browser.esta_logado(page, selectors):
            return {
                "ok": False,
                "erro": "Sessão expirada. Rode o login novamente."
            }

        resultado = executar_lancamento(
            page,
            browser,
            selectors,
            dados,
            dry_run=dry_run,
            condominio=cond,
        )

        return {
            "ok": resultado.ok,
            "status": resultado.status,
            "mensagem": resultado.mensagem,
            "evidencias": resultado.evidencias,
        }