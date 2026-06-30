"""Base dos Page Objects (Módulo 5).

Centraliza a resolução de seletores com cadeia de fallback: tenta cada seletor
da lista até encontrar um elemento presente. Isola o resto do código das
mudanças de layout do Almah.
"""
from __future__ import annotations
from playwright.sync_api import Page, Locator

from core.config.selectors import Selectors
from core.logging.logger import get_logger

log = get_logger("page")


class BasePage:
    def __init__(self, page: Page, selectors: Selectors):
        self.page = page
        self.sel = selectors

    def localizar(self, dotted: str) -> Locator:
        """Primeiro seletor da cadeia que casar com algum elemento."""
        ultimo_erro = None
        for s in self.sel.chain(dotted):
            loc = self.page.locator(s)
            try:
                if loc.count() > 0:
                    return loc.first
            except Exception as e:
                ultimo_erro = e
        log.warning("Nenhum seletor de '%s' encontrado na página.", dotted)
        # devolve o primeiro mesmo assim, para erro explícito a jusante
        return self.page.locator(self.sel.chain(dotted)[0]).first

    def clicar(self, dotted: str) -> None:
        self.localizar(dotted).click()

    def texto(self, dotted: str) -> str:
        return (self.localizar(dotted).text_content() or "").strip()
