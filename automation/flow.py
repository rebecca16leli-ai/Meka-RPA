"""Orquestração do lançamento ponta a ponta (Módulo 5).

Recebe um lançamento JÁ APROVADO (dict) e executa no Almah:
  validar condomínio (R1) -> Contas a Pagar -> buscar fornecedor ->
  escolher a linha da competência -> abrir -> editar -> anexar ->
  (dry-run: parar e printar) OU (confirmar: salvar e validar).
"""
from __future__ import annotations
from dataclasses import dataclass

from playwright.sync_api import Page

from automation.browser import BrowserManager
from automation.pages.condominio_page import CondominioPage
from automation.pages.estabelecimento_page import EstabelecimentoPage
from automation.pages.contas_pagar_page import ContasAPagarPage
from automation.pages.lancamento_page import LancamentoPage
from core.config.selectors import Selectors
from core.domain.competencia import validar_competencia, atualizar_referencia
from core.domain.fornecedores import DeParaFornecedores, montar_complemento
from core.logging.logger import get_logger, salvar_evidencia

log = get_logger("flow")


@dataclass
class ResultadoLancamento:
    ok: bool
    status: str          # 'previa' | 'salvo' | 'revisao' | 'erro'
    mensagem: str
    evidencias: list[str]


def _valor_br(valor: float) -> str:
    return f"{valor:.2f}".replace(".", ",")


def _para_float(txt: str) -> float:
    t = txt.replace("R$", "").replace(".", "").replace(",", ".").strip()
    try:
        return float(t)
    except ValueError:
        return -1.0


def executar_lancamento(page: Page, browser: BrowserManager, selectors: Selectors,
                        dados: dict, dry_run: bool = True) -> ResultadoLancamento:
    evid: list[str] = []
    ref = dados.get("fornecedor_codigo", "lanc")

    # 0) validações de entrada
    competencia = dados["competencia"]
    validar_competencia(competencia)

    # de-para do fornecedor (só para o nome; a CONTA é lida da própria
    # recorrência e mantida — não dependemos mais de conta pré-cadastrada)
    depara = DeParaFornecedores()
    forn = depara.resolver(dados["fornecedor_codigo"])
    # se veio de extração de PDF marcada para revisão, não lança
    if dados.get("_extracao", {}).get("precisa_revisao"):
        avisos = "; ".join(dados["_extracao"].get("avisos", [])) or "extração não confiável"
        return ResultadoLancamento(False, "revisao",
                                   f"Extração dos PDFs precisa de revisão: {avisos}.", evid)

    # 1) condomínio (R1 — validação obrigatória)
    # 1a) tela de entrada: se aparecer, entra JÁ no condomínio do lançamento
    estab = EstabelecimentoPage(page, selectors)
    if estab.esta_na_tela():
        estab.entrar(dados["condominio"])
    # 1b) na tela principal: valida o condomínio ativo (e troca via #btn-condominio se divergir)
    cond = CondominioPage(page, selectors, browser)
    cond.validar_ativo(dados["condominio"], lancamento_ref=ref)
    evid.append(str(salvar_evidencia(page, "01_condominio_ok", ref)))

    # 2) Contas a Pagar + busca + competência
    cap = ContasAPagarPage(page, selectors)
    cap.abrir()
    cap.buscar(dados.get("fornecedor_nome") or forn.nome_almah)
    evid.append(str(salvar_evidencia(page, "02_busca", ref)))
    linha = cap.selecionar_recorrencia(filtro=dados.get("filtro_descricao"))  # erros sobem
    cap.abrir_lancamento(linha)

    # 3) edição do formulário
    form = LancamentoPage(page, selectors)
    # lê a linha existente ANTES de limpar, para MANTER a mesma conta
    conta_atual, compl_atual = form.ler_linha_existente()
    if not conta_atual:
        return ResultadoLancamento(False, "revisao",
            "Não foi possível ler a conta da recorrência (linha de valor vazia). Revisar.", evid)
    # complemento: mantém o texto-base existente e atualiza a competência;
    # se não houver base, usa o complemento informado ou a descrição padrão
    base = compl_atual or dados.get("complemento") or montar_complemento(forn.descricao_padrao, "")
    complemento = atualizar_referencia(base, competencia)

    if not dados.get("emissao") or not dados.get("vencimento"):
        return ResultadoLancamento(False, "revisao",
            "Datas incompletas (emissão/vencimento não lidos). Revisar.", evid)
    if dados.get("documento_referencia"):
        form.set_documento_referencia(dados["documento_referencia"])
    form.set_descricao(complemento)  # Descrição = mesmo texto do complemento
    form.set_datas(dados["emissao"], dados["vencimento"], dados.get("prev_pagto"))
    form.limpar_grade_valor()
    form.adicionar_linha_valor(_valor_br(dados["valor_liquido"]), conta_atual, complemento)

    # 4) anexos
    anexos = dados.get("anexos", [])
    if anexos:
        form.anexar(anexos)
    # evidências de conferência: topo (valor/conta/complemento) e anexos
    form.rolar_para_topo()
    page.wait_for_timeout(400)
    evid.append(str(salvar_evidencia(page, "03_formulario_topo", ref, full_page=False)))
    form.rolar_para_anexos()
    page.wait_for_timeout(400)
    evid.append(str(salvar_evidencia(page, "03_formulario_anexos", ref, full_page=False)))

    # 5) validação do total antes de qualquer salvamento
    total = _para_float(form.ler_total())
    esperado = round(float(dados["valor_liquido"]), 2)
    if abs(total - esperado) > 0.01:
        evid.append(str(salvar_evidencia(page, "ERRO_total_divergente", ref)))
        return ResultadoLancamento(False, "erro",
            f"Total na tela ({total}) difere do esperado ({esperado}). Não salvo.", evid)

    # 6) dry-run para conferência humana, ou salvar
    if dry_run:
        log.info("DRY-RUN: tudo preenchido e validado. NÃO salvando. Confira o print.")
        return ResultadoLancamento(True, "previa",
            "Prévia pronta para conferência. Rode com --confirmar para salvar.", evid)

    form.salvar()
    evid.append(str(salvar_evidencia(page, "04_salvo", ref)))
    return ResultadoLancamento(True, "salvo", "Lançamento salvo com sucesso.", evid)
