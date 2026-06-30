"""Tela de entrada (Estabelecimento) — anterior à tela principal (Módulo 5).

O Almah abre numa tela onde é preciso escolher um estabelecimento (condomínio)
e clicar em Entrar para acessar o sistema. Entramos JÁ no condomínio do
lançamento, reduzindo trocas e risco (a validação na tela principal continua).
"""
from __future__ import annotations
from playwright.sync_api import Page

from automation.pages.base_page import BasePage
from automation import select2
from core.config.selectors import Selectors
from core.logging.logger import get_logger

log = get_logger("estabelecimento")


class EstabelecimentoPage(BasePage):
    def __init__(self, page: Page, selectors: Selectors):
        super().__init__(page, selectors)

    def esta_na_tela(self) -> bool:
        """True se estamos na tela de entrada. Detecta pelo Select2 do
        estabelecimento (sempre presente) — o botão Entrar pode só aparecer
        depois de escolher um estabelecimento, então não serve para detectar."""
        try:
            if "estabelecimento" in self.page.url.lower():
                return True
            sel = self.page.locator(self.sel.chain("estabelecimento.select2_abrir")[0]).first
            return sel.count() > 0 and sel.is_visible()
        except Exception:
            return False

    def entrar(self, condominio: str) -> None:
        log.info("Tela de entrada: selecionando estabelecimento '%s'", condominio)
        abrir = self.page.locator(self.sel.chain("estabelecimento.select2_abrir")[0]).first
        select2.escolher(self.page, abrir, condominio, conter=False)
        self.clicar("estabelecimento.botao_entrar")
        self.page.wait_for_load_state("networkidle")
        # espera a tela principal (nome do condomínio no topo) aparecer
        self.page.wait_for_selector(self.sel.chain("condominio.nome_ativo")[0], timeout=20000)
        log.info("Entrou no sistema.")
