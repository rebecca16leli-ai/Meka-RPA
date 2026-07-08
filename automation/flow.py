from __future__ import annotations

from dataclasses import dataclass, field

from playwright.sync_api import Page

from automation.browser import BrowserManager
from automation.pages.condominio_page import CondominioPage
from automation.pages.estabelecimento_page import EstabelecimentoPage
from automation.pages.contas_pagar_page import ContasAPagarPage
from automation.pages.lancamento_page import LancamentoPage
from core.config.selectors import Selectors
from core.domain.competencia import validar_competencia, atualizar_referencia
from core.logging.logger import get_logger

log = get_logger("flow")


@dataclass
class ResultadoLancamento:
    ok: bool
    status: str  # "previa" | "salvo" | "revisao" | "erro"
    mensagem: str
    evidencias: list[str] = field(default_factory=list)


def _valor_br(valor: float) -> str:
    return f"{valor:.2f}".replace(".", ",")


def _para_float(txt: str) -> float:
    valor = (
        txt.replace("R$", "")
        .replace(".", "")
        .replace(",", ".")
        .strip()
    )

    try:
        return float(valor)
    except ValueError:
        return -1.0


def executar_lancamento(
    page: Page,
    browser: BrowserManager,
    selectors: Selectors,
    dados: dict,
    condominio: str,
    dry_run: bool = True,
) -> ResultadoLancamento:
    print(f"INFO: Abrindo página de estabelecimento - {condominio}")

    estab = EstabelecimentoPage(page, selectors)

    if estab.esta_na_tela(): estab.entrar(condominio)

    print("INFO: Validando condomínio e redirecionando")

    cond = CondominioPage(page, selectors, browser)
    cond.validar_ativo(condominio, lancamento_ref=None)

    print("INFO: Abrindo contas a pagar")

    cap = ContasAPagarPage(page, selectors)
    cap.abrir()

    documentos = dados.get("documentos", [])

    if not documentos:
        return ResultadoLancamento(
            ok=False,
            status="revisao",
            mensagem="Nenhum documento encontrado para lançamento.",
        )

    print("INFO: Iterando os dados da IA")

    for item in documentos:
        competencia = item.get("competencia")
        fornecedor_nome = item.get("fornecedor_nome")
        filtro = item.get("filtro_descricao")
        emissao = item.get("emissao")
        vencimento = item.get("vencimento")
        referencia = item.get("referencia")
        documento_referencia = item.get("documento_referencia")
        previsao_pagamento = item.get("prev_pgto")
        complemento_documento = item.get("complemento")
        valor = item.get("valor_liquido")
        anexos = item.get("anexos", [])

        if valor is None:
            return ResultadoLancamento(
                ok=False,
                status="revisao",
                mensagem="Valor líquido não informado.",
            )

        validar_competencia(competencia)

        cap.buscar(fornecedor_nome)

        linha = cap.selecionar_recorrencia(
            filtro=filtro or None
        )

        cap.abrir_lancamento(linha)

        form = LancamentoPage(page, selectors)

        conta_atual, complemento_atual = form.ler_linha_existente()

        if not conta_atual:
            return ResultadoLancamento(
                ok=False,
                status="revisao",
                mensagem=(
                    "Não foi possível ler a conta da recorrência. "
                    "Revise o lançamento."
                ),
            )

        base_complemento = complemento_atual or complemento_documento or ""
        complemento = atualizar_referencia(
            base_complemento,
            competencia,
        )

        if not emissao or not vencimento:
            return ResultadoLancamento(
                ok=False,
                status="revisao",
                mensagem=(
                    "Datas incompletas. Emissão ou vencimento "
                    "não foram identificados."
                ),
            )

        if referencia and documento_referencia:
            form.set_documento_referencia(documento_referencia)

        form.set_descricao(complemento)
        form.set_datas(
            emissao,
            vencimento,
            previsao_pagamento,
        )

        form.limpar_grade_valor()

        form.adicionar_linha_valor(
            _valor_br(float(valor)),
            conta_atual,
            complemento,
        )

        if anexos:
            form.anexar(anexos)

        form.rolar_para_topo()
        page.wait_for_timeout(400)

        form.rolar_para_anexos()
        page.wait_for_timeout(400)

        total = _para_float(form.ler_total())
        esperado = round(float(valor), 2)

        if abs(total - esperado) > 0.01:
            return ResultadoLancamento(
                ok=False,
                status="erro",
                mensagem=(
                    f"Total na tela ({total}) difere do esperado "
                    f"({esperado}). O lançamento não foi salvo."
                ),
            )

        if dry_run:
            form.localizar("voltar.botao").click()
        else:
            form.salvar()

    return ResultadoLancamento(
        ok=True,
        status="previa" if dry_run else "salvo",
        mensagem=(
            "Prévia processada com sucesso."
            if dry_run
            else "Lançamento salvo com sucesso."
        ),
    )
