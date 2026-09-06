"""Navegacao e selecao segura de recorrencias em Contas a Pagar."""
from __future__ import annotations

import re

from playwright.sync_api import Locator, Page

from automation.pages.base_page import BasePage
from core.config.selectors import Selectors
from core.domain.text_utils import normalizar
from core.logging.logger import get_logger

log = get_logger("contas_pagar")

MES_ANO_RE = re.compile(r"\b(0[1-9]|1[0-2])\s*[/.-]\s*(\d{4})\b")
DATA_RE = re.compile(r"\b\d{2}/\d{2}/(?:\d{2}|\d{4})\b")


def extrair_mes_ano(*valores: str | None) -> str | None:
    """Retorna MM/AAAA a partir de 'REF. MM/AAAA' ou da competencia."""
    for valor in valores:
        match = MES_ANO_RE.search(str(valor or ""))
        if match:
            return f"{match.group(1)}/{match.group(2)}"
    return None


def fornecedor_usa_matricula(fornecedor_nome: str | None) -> bool:
    nome = normalizar(fornecedor_nome)
    return "copel" in nome or "sanepar" in nome


def fornecedor_e_copel(fornecedor_nome: str | None) -> bool:
    return "copel" in normalizar(fornecedor_nome)


def fornecedor_e_sanepar(fornecedor_nome: str | None) -> bool:
    return "sanepar" in normalizar(fornecedor_nome)


def matricula_numerica(matricula: str | None) -> str | None:
    digitos = re.sub(r"\D", "", str(matricula or ""))
    return digitos or None


def matricula_sanepar(matricula: str | None) -> str | None:
    """Preserva a pontuacao da matricula da SANEPAR como consta na fatura."""
    valor = str(matricula or "").strip()
    return valor or None


def ultimos_quatro_matricula(matricula: str | None) -> str | None:
    digitos = matricula_numerica(matricula) or ""
    return digitos[-4:] if len(digitos) >= 4 else None


def termo_busca_recorrencia(
    fornecedor_nome: str | None,
    matricula: str | None,
) -> str | None:
    if fornecedor_e_copel(fornecedor_nome):
        return ultimos_quatro_matricula(matricula)
    if fornecedor_e_sanepar(fornecedor_nome):
        return matricula_sanepar(matricula)
    return fornecedor_nome


def documento_do_lancamento(
    fornecedor_nome: str | None,
    matricula: str | None,
    documento_referencia: str | None,
) -> str | None:
    """A busca pode ser reduzida, mas o Documento usa a matricula completa."""
    if fornecedor_e_copel(fornecedor_nome):
        return matricula_numerica(matricula)
    if fornecedor_e_sanepar(fornecedor_nome):
        return matricula_sanepar(matricula)
    return documento_referencia


class RecorrenciaNaoEncontradaError(RuntimeError):
    pass


class RecorrenciaAmbiguaError(RuntimeError):
    pass


class ContasAPagarPage(BasePage):
    def __init__(self, page: Page, selectors: Selectors):
        super().__init__(page, selectors)

    def abrir(self) -> None:
        log.info("Acessando Financeiro > Contas a Pagar")
        self.clicar("menu.financeiro")
        self.localizar("menu.contas_a_pagar").click()
        self.page.wait_for_load_state("networkidle")
        if "FIN00601" in self.page.url:
            log.info("URL confirma tela de Contas a Pagar (FIN00601).")
        self.page.wait_for_selector(
            self.sel.chain("recorrencia.linha_tabela")[0],
            timeout=15000,
        )

    def buscar(self, fornecedor_nome: str) -> None:
        log.info("Buscando fornecedor: %s", fornecedor_nome)
        campo = self.localizar("recorrencia.campo_busca")
        campo.click()
        campo.fill("")
        campo.press_sequentially(fornecedor_nome, delay=40)
        self.page.wait_for_timeout(1500)

    def _tabela(self) -> Locator:
        return self.page.locator("table.dataTable").first

    def _indice_coluna(self, titulo: str) -> int:
        ths = self._tabela().locator("thead th")
        for i in range(ths.count()):
            if titulo in (ths.nth(i).text_content() or "").strip().lower():
                return i
        return -1

    @staticmethod
    def _texto_celula(linha: Locator, indice: int) -> str:
        celulas = linha.locator("td")
        if 0 <= indice < celulas.count():
            return (celulas.nth(indice).text_content() or "").strip()
        return ""

    def _linhas_validas(self, linhas: Locator, idx_venc: int) -> list[int]:
        candidatas: list[int] = []
        for i in range(linhas.count()):
            linha = linhas.nth(i)
            texto = (linha.text_content() or "").strip()
            vencimento = self._texto_celula(linha, idx_venc) or texto
            if DATA_RE.search(vencimento):
                candidatas.append(i)
        return candidatas

    def _filtrar_por_texto(
        self,
        linhas: Locator,
        indices: list[int],
        alvo: str,
        idx_doc: int,
        somente_doc: bool,
    ) -> list[int]:
        chave = normalizar(alvo)
        resultado = []
        for i in indices:
            linha = linhas.nth(i)
            doc = self._texto_celula(linha, idx_doc)
            texto = doc if somente_doc else (linha.text_content() or "")
            if chave and chave in normalizar(texto):
                resultado.append(i)
        return resultado

    def selecionar_recorrencia(
        self,
        fornecedor_nome: str | None = None,
        filtro: str | None = None,
        documento_referencia: str | None = None,
        competencia: str | None = None,
    ) -> Locator:
        """Seleciona uma unica recorrencia usando a regra do fornecedor.

        COPEL/SANEPAR usam matricula. Os demais usam o mes/ano da referencia
        encontrada no documento, procurando primeiro na coluna Doc.
        """
        linhas = self._tabela().locator("tbody tr")
        if linhas.count() == 0:
            raise RecorrenciaNaoEncontradaError("Nenhuma recorrencia apos a busca.")

        idx_venc = self._indice_coluna("vencimento")
        idx_doc = self._indice_coluna("doc")
        candidatas = self._linhas_validas(linhas, idx_venc)
        if not candidatas:
            raise RecorrenciaNaoEncontradaError(
                "Nenhuma linha de recorrencia valida apos a busca."
            )

        estrategia = "linha unica"
        if fornecedor_usa_matricula(fornecedor_nome):
            if not filtro:
                raise RecorrenciaAmbiguaError(
                    f"{len(candidatas)} recorrencias para {fornecedor_nome}. "
                    "A IA nao retornou a matricula em filtro_descricao."
                )
            filtro_matricula = (
                ultimos_quatro_matricula(filtro)
                if fornecedor_e_copel(fornecedor_nome)
                else matricula_sanepar(filtro)
            )
            if not filtro_matricula:
                raise RecorrenciaAmbiguaError(
                    f"Matricula invalida para {fornecedor_nome}: '{filtro}'."
                )
            estrategia = f"matricula {filtro_matricula}"
            filtradas = self._filtrar_por_texto(
                linhas, candidatas, filtro_matricula, idx_doc, somente_doc=True
            )
            if not filtradas:
                filtradas = self._filtrar_por_texto(
                    linhas, candidatas, filtro_matricula, idx_doc, somente_doc=False
                )
            candidatas = filtradas

        elif len(candidatas) > 1:
            referencia = extrair_mes_ano(documento_referencia, competencia)
            if not referencia:
                raise RecorrenciaAmbiguaError(
                    f"{len(candidatas)} recorrencias para {fornecedor_nome}. "
                    "A IA nao retornou mes/ano em documento_referencia ou competencia."
                )
            estrategia = f"referencia {referencia}"
            filtradas = self._filtrar_por_texto(
                linhas, candidatas, referencia, idx_doc, somente_doc=True
            )
            if not filtradas:
                filtradas = self._filtrar_por_texto(
                    linhas, candidatas, referencia, idx_doc, somente_doc=False
                )
            candidatas = filtradas

        if not candidatas:
            raise RecorrenciaNaoEncontradaError(
                f"Nenhuma recorrencia de {fornecedor_nome} corresponde a {estrategia}."
            )
        if len(candidatas) > 1:
            raise RecorrenciaAmbiguaError(
                f"{len(candidatas)} recorrencias de {fornecedor_nome} correspondem a "
                f"{estrategia}. Processo interrompido para revisao."
            )

        log.info("Recorrencia selecionada por %s.", estrategia)
        return linhas.nth(candidatas[0])

    def abrir_lancamento(self, linha: Locator) -> None:
        linha.dblclick()
        self.page.wait_for_load_state("networkidle")
        self.page.wait_for_selector(
            self.sel.chain("salvar.botao")[0],
            timeout=15000,
        )
        log.info("Lancamento aberto para edicao.")
