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
from core.logging.logger import get_logger, salvar_evidencia
# from core.domain.fornecedores import DeParaFornecedores, montar_complemento

log = get_logger("flow")

@dataclass
class ResultadoLancamento:
    ok: bool
    status: str  # 'previa' | 'salvo' | 'revisao' | 'erro'
    mensagem: str
    evidencias: list[str]


def _valor_br(valor: float) -> str: return f"{valor:.2f}".replace(".", ",")

def _para_float(txt: str) -> float:
    t = txt.replace("R$", "").replace(".", "").replace(",", ".").strip()
    try: return float(t)
    except ValueError: return -1.0

def executar_lancamento(page: Page, browser: BrowserManager, selectors: Selectors, dados: dict, dry_run: bool = True, condominio: str = None,) -> ResultadoLancamento:
    print("INFO: Abrindo pagin de condominio")
    estab = EstabelecimentoPage(page, selectors)
    if estab.esta_na_tela(): estab.entrar(condominio)

    # Na tela principal: valida o condomínio ativo (e troca via #btn-condominio se divergir)
    print("INFO: Validando condominio e redirecionando")
    cond = CondominioPage(page, selectors, browser)
    cond.validar_ativo(condominio, lancamento_ref=None)

    # Contas a Pagar + busca + competência
    print("INFO: Abrindo contas a pagar >> busca >> competencia")
    cap = ContasAPagarPage(page, selectors)
    cap.abrir()
    
    print("INFO: Iterando os dados da IA")
    # Itera os dados
    for item in dados["documentos"]:
        competencia = item.get("competencia")
        ref = item.get("fornecedor_codigo")
        forn_nome = item.get("fornecedor_nome")
        filtro = item.get("filtro_descricao")
        emissao = item.get("emissao")
        vencimento = item.get("vencimento")
        data_ref = item.get("referencia")
        doc_ref = item.get("documento_referencia")
        prev_pgto = item.get("prev_pgto")
        complementod = item.get("complemento")
        valor = item.get("valor_liquido")

        validar_competencia(competencia)
        cap.buscar(forn_nome)
        linha = cap.selecionar_recorrencia(filtro=filtro or None)
        cap.abrir_lancamento(linha)

        # Edição de Formulario
        form = LancamentoPage(page, selectors)
        conta_atual, compl_atual = form.ler_linha_existente()
        if not conta_atual: return ResultadoLancamento(False, "revisao", "Não foi possível ler a conta da recorrência (linha de valor vazia). Revisar.",)

        base = compl_atual or complementod
        complemento = atualizar_referencia(base, competencia)

        if not emissao or not vencimento: return ResultadoLancamento(False, "revisao",  "Datas incompletas (emissão/vencimento não lidos). Revisar.",)
            
        if data_ref: form.set_documento_referencia(doc_ref)
        form.set_descricao(complemento)  # Descrição = mesmo texto do complemento
        form.set_datas(emissao, vencimento, prev_pgto)
        form.limpar_grade_valor()
        form.adicionar_linha_valor(_valor_br(valor), conta_atual, complemento )

        # Anexos
        anexos = item.get("anexos", [])
        if anexos: form.anexar(anexos)

        # Evidências de conferênci
        form.rolar_para_topo()
        page.wait_for_timeout(400)
        form.rolar_para_anexos()
        page.wait_for_timeout(400)

        # Validação do total antes de qualquer salvamento
        total = _para_float(form.ler_total())
        esperado = round(float(item["valor_liquido"]), 2)
        if abs(total - esperado) > 0.01: return ResultadoLancamento(False, "erro", f"Total na tela ({total}) difere do esperado ({esperado}). Não salvo.")
        form.localizar("voltar.botao").click()
    form.salvar()
    return ResultadoLancamento(True, "salvo", "Lançamento salvo com sucesso.")
