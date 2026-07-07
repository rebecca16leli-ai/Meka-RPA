"""Contas a Pagar: navegação, busca e seleção da recorrência (Módulo 5)."""
from __future__ import annotations
from playwright.sync_api import Page, Locator

from automation.pages.base_page import BasePage
from core.config.selectors import Selectors
from core.domain.text_utils import normalizar
from core.logging.logger import get_logger
import re

log = get_logger("contas_pagar")


class RecorrenciaNaoEncontradaError(RuntimeError):
    pass


class RecorrenciaAmbiguaError(RuntimeError):
    """Mais de uma linha bate com a competência -> revisão humana."""


class ContasAPagarPage(BasePage):
    def __init__(self, page: Page, selectors: Selectors):
        super().__init__(page, selectors)

    def abrir(self) -> None:
        log.info("Acessando Financeiro > Contas a Pagar")
        self.clicar("menu.financeiro")
        self.localizar("menu.contas_a_pagar").click()
        self.page.wait_for_load_state("networkidle")
        # verificação extra de tela (não dependemos só dela)
        if "FIN00601" in self.page.url:
            log.info("URL confirma tela de Contas a Pagar (FIN00601).")
        self.page.wait_for_selector(self.sel.chain("recorrencia.linha_tabela")[0], timeout=15000)

    def buscar(self, fornecedor_nome: str) -> None:
        log.info("Buscando fornecedor: %s", fornecedor_nome)
        campo = self.localizar("recorrencia.campo_busca")
        campo.click()
        campo.fill("")
        # digita caractere a caractere para disparar o filtro do DataTables (keyup)
        campo.press_sequentially(fornecedor_nome, delay=40)
        self.page.wait_for_timeout(1500)

    def _tabela(self):
        return self.page.locator("table.dataTable").first

    def _indice_coluna(self, titulo: str) -> int:
        """Índice da coluna pelo título no cabeçalho (robusto a reordenação)."""
        ths = self._tabela().locator("thead th")
        for i in range(ths.count()):
            if titulo in (ths.nth(i).text_content() or "").strip().lower():
                return i
        return -1

    def selecionar_recorrencia(self, filtro: str | None = None) -> Locator:
        """Seleciona a recorrência do fornecedor JÁ filtrado pela busca.

        Regra (confirmada com o cliente):
          - a maioria dos fornecedores tem UMA só linha -> usa ela;
          - COPEL/SANEPAR têm várias -> desempata por `filtro` (a MATRÍCULA,
            que fica na coluna 'Doc' do Almah e também no boleto);
          - se sobrar mais de uma sem como desempatar -> ERRO (revisão).
        Não casa por data: a competência do lançamento NÃO bate com o
        vencimento da recorrência (pode ser de meses atrás)."""
        
        tabela = self._tabela()
        linhas = tabela.locator("tbody tr")
        total = linhas.count()
        if total == 0:
            raise RecorrenciaNaoEncontradaError("Nenhuma recorrência após a busca.")

        idx_venc = self._indice_coluna("vencimento")
        idx_doc = self._indice_coluna("doc")
        data_re = re.compile(r"\d{2}/\d{2}/\d{4}")

        # linhas de dados = têm uma data no Vencimento (exclui SUBTOTAL/TOTAL)
        candidatas: list[int] = []
        for i in range(total):
            tds = linhas.nth(i).locator("td")
            n = tds.count()
            if n == 0:
                continue
            venc_txt = (tds.nth(idx_venc).text_content() if 0 <= idx_venc < n
                        else linhas.nth(i).text_content()) or ""
            if data_re.search(venc_txt):
                candidatas.append(i)

        if not candidatas:
            raise RecorrenciaNaoEncontradaError("Nenhuma linha de recorrência válida após a busca.")

        # desempate por matrícula/descrição (COPEL/SANEPAR ou outros com várias)
        if filtro:
            alvo = normalizar(filtro)
            filtradas = []
            for i in candidatas:
                tds = linhas.nth(i).locator("td")
                n = tds.count()
                doc_txt = tds.nth(idx_doc).text_content() if 0 <= idx_doc < n else ""
                if alvo == normalizar(doc_txt) or alvo in normalizar(linhas.nth(i).text_content() or ""):
                    filtradas.append(i)
            candidatas = filtradas

        if len(candidatas) == 0:
            raise RecorrenciaNaoEncontradaError(
                "Nenhuma recorrência" + (f" com o filtro '{filtro}'." if filtro else "."))
        if len(candidatas) > 1:
            raise RecorrenciaAmbiguaError(
                f"{len(candidatas)} recorrências para este fornecedor"
                + (f" mesmo com o filtro '{filtro}'" if filtro else "")
                + ". Para COPEL/SANEPAR, informe a matrícula no campo de filtro. Revisão.")
        log.info("Recorrência selecionada (filtro=%s).", filtro or "—")
        return linhas.nth(candidatas[0])

    def abrir_lancamento(self, linha: Locator) -> None:
        linha.dblclick()
        self.page.wait_for_load_state("networkidle")
        # confirma que o modal de Alteração abriu (botão salvar presente)
        self.page.wait_for_selector(self.sel.chain("salvar.botao")[0], timeout=15000)
        log.info("Lançamento aberto para edição.")
