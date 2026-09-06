"""Valida login e selecao de condominio pelo fluxo real do executavel."""
from __future__ import annotations

import argparse

from automation.browser import BrowserManager
from automation.pages.condominio_page import CondominioDivergenteError, CondominioPage
from automation.pages.estabelecimento_page import EstabelecimentoPage
from automation.pages.login_page import LoginPage
from core.config.selectors import Selectors, SeletorIndisponivelError
from core.logging.logger import get_logger

log = get_logger("worker")


def executar(nome_condominio: str) -> int:
    selectors = Selectors()
    browser = BrowserManager()
    try:
        with browser.pagina() as page:
            LoginPage(page).autenticar()
            estabelecimento = EstabelecimentoPage(page, selectors)
            if estabelecimento.esta_na_tela():
                estabelecimento.entrar(nome_condominio)
            CondominioPage(page, selectors, browser).validar_ativo(nome_condominio)
            log.info("Login e condominio validados com sucesso.")
            return 0
    except SeletorIndisponivelError as exc:
        log.error("Seletor ausente: %s", exc)
        return 3
    except CondominioDivergenteError as exc:
        log.error("Parada de seguranca: %s", exc)
        return 4
    except Exception:
        log.exception("Falha ao validar o fluxo")
        return 2


def main() -> None:
    parser = argparse.ArgumentParser(description="Valida login e condominio no Almah")
    parser.add_argument("--condominio", required=True)
    args = parser.parse_args()
    raise SystemExit(executar(args.condominio))


if __name__ == "__main__":
    main()
