from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from playwright.sync_api import Page

from automation.browser import BrowserManager
from automation.pages.condominio_page import CondominioPage
from automation.pages.contas_pagar_page import (
    ContasAPagarPage,
    documento_do_lancamento,
    fornecedor_e_copel,
    fornecedor_e_sanepar,
    matricula_sanepar,
    termo_busca_recorrencia,
    ultimos_quatro_matricula,
)
from automation.pages.estabelecimento_page import EstabelecimentoPage
from automation.pages.lancamento_page import LancamentoPage
from core.config.selectors import Selectors
from core.domain.competencia import (
    atualizar_referencia,
    montar_descricao_copel,
    montar_descricao_sanepar,
    validar_competencia,
)
from core.logging.logger import (
    criar_pasta_execucao,
    criar_pasta_lancamento,
    get_logger,
    salvar_evidencia,
)

log = get_logger("flow")


@dataclass
class ResultadoLancamento:
    ok: bool
    status: str
    mensagem: str
    evidencias: list[str] = field(default_factory=list)
    itens: list[dict] = field(default_factory=list)


def _valor_br(valor: float) -> str:
    return f"{valor:.2f}".replace(".", ",")


def _para_float(txt: str) -> float:
    valor = txt.replace("R$", "").replace(".", "").replace(",", ".").strip()
    try:
        return float(valor)
    except ValueError:
        return -1.0


def _capturar(
    page: Page,
    pasta: Path,
    etapa: str,
    evidencias: list[str],
) -> None:
    """A falha de um print e registrada, mas nunca mascara o erro do robo."""
    try:
        caminho = salvar_evidencia(page, etapa, pasta=pasta)
        evidencias.append(str(caminho))
        log.info("Evidencia salva: %s", caminho)
    except Exception:
        log.exception("Nao foi possivel salvar a evidencia '%s'", etapa)


def _interromper(
    page: Page,
    pasta: Path,
    evidencias: list[str],
    mensagem: str,
    status: str = "revisao",
) -> ResultadoLancamento:
    _capturar(page, pasta, f"98_{status}", evidencias)
    return ResultadoLancamento(False, status, mensagem, evidencias.copy())


def _executar_documento(
    page: Page,
    cap: ContasAPagarPage,
    selectors: Selectors,
    item: dict,
    dry_run: bool,
    pasta: Path,
    evidencias: list[str],
) -> ResultadoLancamento | None:
    competencia = item.get("competencia")
    fornecedor_nome = item.get("fornecedor_nome")
    filtro = item.get("filtro_descricao")
    emissao = item.get("emissao")
    vencimento = item.get("vencimento")
    documento_referencia = item.get("documento_referencia")
    previsao_pagamento = item.get("prev_pagto") or item.get("prev_pgto")
    complemento_documento = item.get("complemento")
    valor = item.get("valor_liquido")
    consumo_kwh = item.get("consumo_kwh")
    consumo_m3 = item.get("consumo_m3")
    anexos = item.get("anexos", [])

    _capturar(page, pasta, "01_condominio_validado", evidencias)

    if not fornecedor_nome:
        return _interromper(page, pasta, evidencias, "Fornecedor nao informado pela IA.")
    if not competencia:
        return _interromper(page, pasta, evidencias, "Competencia nao informada pela IA.")
    if valor is None:
        return _interromper(page, pasta, evidencias, "Valor liquido nao informado.")
    if fornecedor_e_copel(fornecedor_nome) and consumo_kwh is None:
        return _interromper(
            page,
            pasta,
            evidencias,
            "A IA nao encontrou o consumo em kWh no boleto da COPEL.",
        )
    if fornecedor_e_sanepar(fornecedor_nome) and consumo_m3 is None:
        return _interromper(
            page,
            pasta,
            evidencias,
            "A IA nao encontrou o consumo em m3 na fatura da SANEPAR.",
        )

    # Referencias retroativas sao permitidas. Validamos apenas o formato
    # MM/AAAA para impedir dados malformados, sem limitar mes ou ano.
    validar_competencia(competencia)
    termo_busca = termo_busca_recorrencia(fornecedor_nome, filtro)
    if not termo_busca:
        return _interromper(
            page,
            pasta,
            evidencias,
            "A IA nao retornou uma unidade consumidora valida para a COPEL.",
        )
    filtro_recorrencia = (
        ultimos_quatro_matricula(filtro)
        if fornecedor_e_copel(fornecedor_nome)
        else matricula_sanepar(filtro)
        if fornecedor_e_sanepar(fornecedor_nome)
        else filtro
    )
    cap.buscar(termo_busca)
    linha = cap.selecionar_recorrencia(
        fornecedor_nome=fornecedor_nome,
        filtro=filtro_recorrencia or None,
        documento_referencia=documento_referencia,
        competencia=competencia,
    )
    _capturar(page, pasta, "02_recorrencia_selecionada", evidencias)

    cap.abrir_lancamento(linha)
    form = LancamentoPage(page, selectors)
    _capturar(page, pasta, "03_formulario_original", evidencias)

    conta_atual, complemento_atual = form.ler_linha_existente()
    if not conta_atual:
        return _interromper(
            page,
            pasta,
            evidencias,
            "Nao foi possivel ler a conta da recorrencia. Revise o lancamento.",
        )
    if not emissao or not vencimento:
        return _interromper(
            page,
            pasta,
            evidencias,
            "Datas incompletas: emissao ou vencimento nao foram identificados.",
        )

    base_complemento = complemento_atual or complemento_documento or ""
    if fornecedor_e_copel(fornecedor_nome):
        complemento = montar_descricao_copel(
            base_complemento,
            competencia,
            consumo_kwh,
        )
    elif fornecedor_e_sanepar(fornecedor_nome):
        complemento = montar_descricao_sanepar(
            base_complemento,
            competencia,
            consumo_m3,
        )
    else:
        complemento = atualizar_referencia(base_complemento, competencia)
    documento = documento_do_lancamento(
        fornecedor_nome,
        filtro,
        documento_referencia,
    )
    if documento:
        form.set_documento_referencia(documento)
    form.set_descricao(complemento)
    form.set_datas(emissao, vencimento, previsao_pagamento)
    form.set_cobranca_recebida_sim()
    form.limpar_grade_valor()
    form.adicionar_linha_valor(_valor_br(float(valor)), conta_atual, complemento)
    if anexos:
        form.anexar(anexos)

    form.rolar_para_topo()
    page.wait_for_timeout(400)
    _capturar(page, pasta, "04_formulario_preenchido", evidencias)

    total = _para_float(form.ler_total())
    esperado = round(float(valor), 2)
    if abs(total - esperado) > 0.01:
        return _interromper(
            page,
            pasta,
            evidencias,
            f"Total na tela ({total}) difere do esperado ({esperado}).",
            status="erro",
        )

    if dry_run:
        _capturar(page, pasta, "05_dry_run_final", evidencias)
        form.localizar("voltar.botao").click()
    else:
        form.salvar()
        _capturar(page, pasta, "05_lancamento_salvo", evidencias)
    return None


def executar_lancamento(
    page: Page,
    browser: BrowserManager,
    selectors: Selectors,
    dados: dict,
    condominio: str,
    dry_run: bool = True,
    pasta_execucao: Path | None = None,
) -> ResultadoLancamento:
    if not isinstance(dados, dict):
        return ResultadoLancamento(False, "revisao", "A IA nao retornou um objeto JSON valido.")
    documentos = dados.get("documentos", [])
    if not documentos:
        return ResultadoLancamento(False, "revisao", "Nenhum documento encontrado para lancamento.")

    pasta_execucao = pasta_execucao or criar_pasta_execucao()
    pasta_geral = pasta_execucao / "00_execucao"
    pasta_geral.mkdir(parents=True, exist_ok=True)
    log.info("Evidencias desta execucao: %s", pasta_execucao)

    estabelecimento = EstabelecimentoPage(page, selectors)
    if estabelecimento.esta_na_tela():
        estabelecimento.entrar(condominio)

    cond = CondominioPage(page, selectors, browser)
    cond.validar_ativo(
        condominio,
        lancamento_ref="execucao",
        pasta_evidencia=pasta_geral,
    )

    cap = ContasAPagarPage(page, selectors)
    resultados: list[dict] = []
    todas_evidencias: list[str] = []

    for indice, item in enumerate(documentos, start=1):
        evidencias: list[str] = []
        pasta = criar_pasta_lancamento(
            pasta_execucao,
            indice,
            item.get("fornecedor_nome"),
            item.get("documento_referencia") or item.get("competencia"),
        )
        try:
            # Garante um ponto de partida conhecido para cada documento sem
            # trocar o navegador, contexto, sessao ou condominio autenticado.
            cap.abrir()
            interrompido = _executar_documento(
                page,
                cap,
                selectors,
                item,
                dry_run,
                pasta,
                evidencias,
            )
            if interrompido is not None:
                resultado_item = interrompido
            else:
                status_item = "previa" if dry_run else "salvo"
                mensagem_item = (
                    "Previa processada com sucesso."
                    if dry_run
                    else "Lancamento salvo com sucesso."
                )
                resultado_item = ResultadoLancamento(
                    True,
                    status_item,
                    mensagem_item,
                    evidencias.copy(),
                )
        except Exception as exc:
            _capturar(page, pasta, "99_erro", evidencias)
            log.exception(
                "Falha no lancamento %d; a fila continuara. Evidencias em %s",
                indice,
                pasta,
            )
            resultado_item = ResultadoLancamento(
                False,
                "erro",
                str(exc) or exc.__class__.__name__,
                evidencias.copy(),
            )

        todas_evidencias.extend(resultado_item.evidencias)
        anexos = item.get("anexos") or []
        resultados.append({
            "indice": indice,
            "ok": resultado_item.ok,
            "status": resultado_item.status,
            "mensagem": resultado_item.mensagem,
            "fornecedor": item.get("fornecedor_nome") or "Fornecedor nao identificado",
            "referencia": item.get("documento_referencia") or item.get("competencia") or "",
            "arquivos": [Path(str(anexo)).name for anexo in anexos],
            "evidencias": resultado_item.evidencias,
        })

    sucessos = sum(1 for item in resultados if item["ok"])
    erros = len(resultados) - sucessos
    status = "concluido" if not erros else "parcial" if sucessos else "erro"
    mensagem = f"Lote concluido: {sucessos} sucesso(s) e {erros} erro(s)."
    return ResultadoLancamento(
        erros == 0,
        status,
        mensagem,
        todas_evidencias,
        resultados,
    )
