"""Formulário de Alteração do lançamento (Módulo 5).

Edita os campos do mês: documento/referência, emissão, vencimento, prev. pagto,
grade de Valor (limpar + adicionar 1 linha com valor/conta/complemento) e anexos.
"""
from __future__ import annotations
import re
from pathlib import Path

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from automation.pages.base_page import BasePage
from automation import select2
from core.config.selectors import Selectors
from core.domain.competencia import data_br
from core.domain.text_utils import normalizar
from core.logging.logger import get_logger

log = get_logger("lancamento")


class LancamentoPage(BasePage):
    ERROS_SALVAR = (
        ".alert-danger, .toast-error, .toast-message, .swal2-html-container, "
        ".help-block, .invalid-feedback, .has-error .control-label"
    )

    def __init__(self, page: Page, selectors: Selectors):
        super().__init__(page, selectors)

    # ---------- campos simples ----------
    def set_documento_referencia(self, texto: str) -> None:
        campo = self.localizar("formulario.documento_referencia")
        campo.fill("")
        campo.fill(texto)

    def set_descricao(self, texto: str) -> None:
        """Descrição (campo de cima) = mesmo texto do complemento. O sistema pode
        ter um valor antigo; escrevemos e conferimos que o nosso prevaleceu."""
        try:
            campo = self.localizar("formulario.descricao")
            for _ in range(3):
                campo.fill("")
                campo.fill(texto)
                self.page.wait_for_timeout(200)
                if (campo.input_value() or "").strip() == texto:
                    break
            else:
                log.warning("Descrição pode não ter prevalecido: '%s'", campo.input_value())
            log.info("Descrição preenchida: '%s'", texto)
        except Exception as e:
            log.warning("Não foi possível preencher a Descrição (conferir seletor #f_descricao): %s", e)

    def _set_data(self, dotted: str, valor) -> None:
        campo = self.localizar(dotted)
        campo.fill("")
        campo.fill(data_br(valor))

    def set_datas(self, emissao, vencimento, prev_pagto=None) -> None:
        self._set_data("formulario.emissao", emissao)
        self._set_data("formulario.vencimento", vencimento)
        self._set_data("formulario.prev_pagto", prev_pagto or vencimento)

    def set_cobranca_recebida_sim(self) -> None:
        abrir = self.localizar("formulario.cobranca_recebida")
        select2.escolher_opcao_fixa(self.page, abrir, "Sim")
        selecionado = (abrir.text_content() or "").strip()
        selecionado_limpo = re.sub(
            r"[^a-z0-9]+",
            " ",
            normalizar(selecionado),
        ).strip()
        if selecionado_limpo != "sim":
            raise RuntimeError(
                f"Cob. Recebida nao ficou como Sim. Valor lido: '{selecionado}'."
            )
        log.info("Cob. Recebida definida como Sim.")

    # ---------- grade de Valor ----------
    def ler_linha_existente(self) -> tuple[str | None, str | None]:
        """Lê a CONTA e o COMPLEMENTO da linha de valor já existente (antes de
        apagar), para manter a mesma conta no lançamento. Colunas: Valor(0),
        Conta(1), Complemento(2)."""
        del_sel = self.sel.chain("formulario.valor_grade_del")[0]
        btn = self.page.locator(del_sel).first
        if btn.count() == 0:
            return None, None
        row = btn.locator("xpath=ancestor::tr[1]")
        tds = row.locator("td")
        n = tds.count()
        conta = (tds.nth(1).text_content() or "").strip() if n > 1 else None
        compl = (tds.nth(2).text_content() or "").strip() if n > 2 else None
        log.info("Linha existente lida: conta='%s' complemento='%s'", conta, compl)
        return conta, compl

    def limpar_grade_valor(self) -> None:
        """Remove todas as linhas de valor existentes (botões de lixeira)."""
        del_sel = self.sel.chain("formulario.valor_grade_del")[0]
        for _ in range(20):  # trava de segurança
            botoes = self.page.locator(del_sel)
            if botoes.count() == 0:
                break
            botoes.first.click()
            self.page.wait_for_timeout(300)
        log.info("Grade de valor limpa.")

    def adicionar_linha_valor(self, valor_str: str, conta_descricao: str, complemento: str) -> None:
        """Adiciona a linha de valor MANTENDO a mesma conta (por descrição)."""
        self.localizar("formulario.valor_grade_input").fill(valor_str)
        # Conta é Select2 dentro da MESMA linha do input #f_valor (escopo seguro)
        abrir_conta = self.page.locator(
            "xpath=//input[@id='f_valor']/ancestor::tr[1]"
        ).locator(".select2-selection--single").first
        select2.escolher_conta(self.page, abrir_conta, conta_descricao)
        # O Almah AUTO-PREENCHE o complemento ao escolher a conta (com a descrição
        # antiga). Esperamos isso ocorrer e então sobrescrevemos com o complemento
        # correto (competência do mês), conferindo que prevaleceu.
        self.page.wait_for_timeout(600)
        comp = self.localizar("formulario.valor_grade_complemento")
        for _ in range(3):
            comp.fill("")
            comp.fill(complemento)
            self.page.wait_for_timeout(250)
            if (comp.input_value() or "").strip() == complemento:
                break
        else:
            log.warning("Complemento pode não ter prevalecido: '%s'", comp.input_value())
        self.localizar("formulario.valor_grade_add").click()
        self.page.wait_for_timeout(400)
        log.info("Linha adicionada: %s / conta '%s' / compl '%s'",
                 valor_str, conta_descricao, complemento)

    def ler_total(self) -> str:
        return (self.localizar("formulario.valor_liquido_total").input_value() or "").strip()

    # ---------- anexos ----------
    def anexar(self, caminhos: list[str]) -> None:
        btn = self.sel.chain("anexos.botao_upload")[0]
        for caminho in caminhos:
            p = Path(caminho)
            if not p.exists():
                raise FileNotFoundError(f"Anexo não encontrado: {caminho}")
            with self.page.expect_file_chooser() as fc_info:
                self.page.locator(btn).first.click()
            fc_info.value.set_files(str(p))
            # O upload e assincrono. Aguardar reduz a chance de salvar enquanto
            # o PDF ainda esta sendo enviado ao Almah.
            self.page.wait_for_timeout(1500)
            log.info("Anexado: %s", p.name)

    # ---------- rolagem para conferência (prints) ----------
    def rolar_para_topo(self) -> None:
        """Traz o início do formulário (documento/valor) para a visão."""
        try:
            self.localizar("formulario.documento_referencia").scroll_into_view_if_needed()
        except Exception:
            pass

    def rolar_para_anexos(self) -> None:
        try:
            self.page.locator(self.sel.chain("anexos.botao_upload")[0]).first.scroll_into_view_if_needed()
        except Exception:
            pass

    # ---------- salvar ----------
    def _erros_visiveis_ao_salvar(self) -> list[str]:
        mensagens: list[str] = []
        candidatos = self.page.locator(self.ERROS_SALVAR)
        for indice in range(candidatos.count()):
            item = candidatos.nth(indice)
            try:
                texto = (item.text_content() or "").strip()
                if item.is_visible() and texto and texto not in mensagens:
                    mensagens.append(texto)
            except Exception:
                continue
        return mensagens

    def salvar(self) -> None:
        botao = self.localizar("salvar.botao")
        botao.click()
        try:
            # A gravacao ocorre via AJAX e nao dispara navegacao. O botao some
            # somente depois que o servidor confirma e fecha o formulario.
            botao.wait_for(state="hidden", timeout=30000)
        except PlaywrightTimeoutError as exc:
            mensagens = self._erros_visiveis_ao_salvar()
            detalhe = f" Mensagem do Almah: {' | '.join(mensagens)}" if mensagens else ""
            raise RuntimeError(
                "O Almah nao confirmou a gravacao: o formulario continuou aberto "
                "apos 30 segundos." + detalhe
            ) from exc

        self.page.wait_for_timeout(400)
        log.info("Lancamento salvo e confirmado pelo fechamento do formulario.")
