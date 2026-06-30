"""Troca e validação do condomínio ativo (Módulo 5 — núcleo do requisito R1).

NUNCA prosseguir para Financeiro sem confirmar que o condomínio ativo é
exatamente o esperado. A confirmação usa dois sinais independentes:
  1) DOM: nome do condomínio ativo no topo da tela.
  2) XHR (opcional): resposta da troca, se XHR_TROCA_CONDOMINIO estiver configurado.
"""
from __future__ import annotations

from playwright.sync_api import Page

from automation.browser import BrowserManager
from automation.pages.base_page import BasePage
from core.config.selectors import Selectors
from core.domain.text_utils import nomes_equivalentes, normalizar
from core.logging.logger import get_logger, salvar_evidencia

log = get_logger("condominio")


class CondominioDivergenteError(RuntimeError):
    """Levantado quando o condomínio ativo não confere com o esperado (R1)."""


class CondominioPage(BasePage):
    def __init__(self, page: Page, selectors: Selectors, browser: BrowserManager):
        super().__init__(page, selectors)
        self.browser = browser

    # ---------------------------------------------------------------- troca
    def trocar(self, nome_esperado: str) -> None:
        """Abre o seletor, busca e seleciona o condomínio pelo texto exato."""
        log.info("Abrindo seletor de condomínio para: %s", nome_esperado)
        self.clicar("condominio.botao_trocar")

        # Select2: digitar no campo de busca e aguardar resultados
        busca = self.localizar("condominio.select2_search_input")
        busca.click()
        busca.fill(nome_esperado)

        opcoes_sel = self.sel.chain("condominio.select2_opcao_resultado")[0]
        self.page.wait_for_selector(opcoes_sel)

        alvo = None
        for i in range(self.page.locator(opcoes_sel).count()):
            opc = self.page.locator(opcoes_sel).nth(i)
            if nomes_equivalentes(opc.text_content(), nome_esperado):
                alvo = opc
                break
        if alvo is None:
            raise CondominioDivergenteError(
                f"Condomínio '{nome_esperado}' não apareceu na lista de busca."
            )
        alvo.click()

        # Confirmar e aguardar carregamento completo (não confiar só no clique)
        self.clicar("condominio.botao_confirmar")
        self.page.wait_for_load_state("networkidle")

    # ------------------------------------------------------------ validação
    def ler_nome_ativo(self) -> str:
        return self.texto("condominio.nome_ativo")

    def _ler_nome_ativo_curto(self) -> str:
        """Leitura rápida e tolerante (não trava nem gera warning longo)."""
        for s in self.sel.chain("condominio.nome_ativo"):
            loc = self.page.locator(s).first
            try:
                if loc.count() > 0:
                    return (loc.text_content(timeout=1500) or "").strip()
            except Exception:
                continue
        return ""

    def validar_ativo(self, nome_esperado: str, lancamento_ref: str = "geral",
                      tentativas: int = 12, intervalo_ms: int = 700) -> None:
        """Confere o condomínio ativo de forma PACIENTE: relê o nome algumas
        vezes (a tela pode levar 1-2s para assentar no condomínio após a entrada).
        NÃO troca de condomínio — a seleção já foi feita na tela de entrada.
        Se, após esperar, continuar divergente, PARA (trava de segurança R1)."""
        ultimo = ""
        for _ in range(tentativas):
            ultimo = self._ler_nome_ativo_curto()
            if ultimo and nomes_equivalentes(ultimo, nome_esperado):
                salvar_evidencia(self.page, "condominio_ativo_ok", lancamento_ref)
                log.info("Condomínio ativo confirmado: %s", nome_esperado)
                return
            self.page.wait_for_timeout(intervalo_ms)

        salvar_evidencia(self.page, "condominio_divergente", lancamento_ref)
        raise CondominioDivergenteError(
            f"Condomínio ativo diverge do esperado '{nome_esperado}'. "
            f"Lido na tela: '{ultimo}'. Processo interrompido."
        )

    def _checar_dom(self, nome_esperado: str) -> bool:
        ativo = self.ler_nome_ativo()
        return nomes_equivalentes(ativo, nome_esperado)

    def _checar_xhr(self, nome_esperado: str) -> bool:
        """Se XHR não estiver configurado, retorna True (validação só por DOM)."""
        resp = self.browser.xhr.ultima("troca_condominio")
        if resp is None:
            return True
        corpo = (resp.get("corpo") or "")
        if resp.get("status", 0) >= 400:
            return False
        # heurística inicial: o nome esperado aparece no corpo da resposta.
        # >>> AJUSTAR após inspeção: comparar pelo ID real do condomínio. <<<
        return normalizar(nome_esperado) in normalizar(corpo)
