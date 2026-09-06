from __future__ import annotations

from threading import Lock
from typing import Any

from automation.browser import BrowserManager
from automation.flow import executar_lancamento
from automation.pages.condominio_page import CondominioPage
from automation.pages.estabelecimento_page import EstabelecimentoPage
from automation.pages.login_page import LoginPage
from core.config.selectors import Selectors, SeletorIndisponivelError
from core.config.settings import settings
from core.logging.logger import criar_pasta_execucao, get_logger, salvar_evidencia

log = get_logger("api")

# O executable atende requisicoes em threads. Impede dois robos de alterarem
# lancamentos ao mesmo tempo no mesmo computador.
_automation_lock = Lock()


def resolver_dry_run(confirmar: bool | None) -> bool:
    return settings.dry_run if confirmar is None else not confirmar


def validar_condominio(condominio: str) -> dict[str, Any]:
    selectors = Selectors()
    browser = BrowserManager()

    with _automation_lock, browser.pagina() as page:
        pasta_execucao = criar_pasta_execucao()
        pasta_geral = pasta_execucao / "00_execucao"
        pasta_geral.mkdir(parents=True, exist_ok=True)
        try:
            LoginPage(page).autenticar()
            login_ev = salvar_evidencia(page, "login_concluido", pasta=pasta_geral)
            estabelecimento = EstabelecimentoPage(page, selectors)
            if estabelecimento.esta_na_tela():
                estabelecimento.entrar(condominio)
            CondominioPage(page, selectors, browser).validar_ativo(
                condominio,
                pasta_evidencia=pasta_geral,
            )
            return {
                "ok": True,
                "mensagem": "Condominio validado.",
                "evidencias": [str(login_ev)],
            }
        except SeletorIndisponivelError as exc:
            try:
                salvar_evidencia(page, "erro_seletor", pasta=pasta_geral)
            except Exception:
                log.exception("Falha ao evidenciar erro de seletor")
            return {"ok": False, "erro": str(exc)}
        except Exception as exc:
            try:
                salvar_evidencia(page, "erro_validacao", pasta=pasta_geral)
            except Exception:
                log.exception("Falha ao evidenciar erro de validacao")
            log.exception("Falha ao validar condominio")
            return {"ok": False, "erro": str(exc)}


def executar_lancamento_json(
    dados: dict[str, Any],
    confirmar: bool | None = None,
    cond: str | None = None,
) -> dict[str, Any]:
    if not cond:
        return {"ok": False, "erro": "Condominio nao informado."}

    selectors = Selectors()
    browser = BrowserManager()
    dry_run = resolver_dry_run(confirmar)

    with _automation_lock, browser.pagina() as page:
        pasta_execucao = criar_pasta_execucao()
        pasta_geral = pasta_execucao / "00_execucao"
        pasta_geral.mkdir(parents=True, exist_ok=True)
        evidencias_gerais: list[str] = []
        # A partir daqui tudo ocorre na mesma pagina e no mesmo contexto:
        # login -> estabelecimento/condominio -> contas a pagar -> lancamento.
        try:
            LoginPage(page).autenticar()
            login_ev = salvar_evidencia(page, "login_concluido", pasta=pasta_geral)
            evidencias_gerais.append(str(login_ev))
            resultado = executar_lancamento(
                page,
                browser,
                selectors,
                dados,
                dry_run=dry_run,
                condominio=cond,
                pasta_execucao=pasta_execucao,
            )
        except Exception:
            try:
                erro_ev = salvar_evidencia(page, "erro_execucao", pasta=pasta_geral)
                evidencias_gerais.append(str(erro_ev))
            except Exception:
                log.exception("Falha ao evidenciar erro geral da execucao")
            raise

        resultado.evidencias = evidencias_gerais + resultado.evidencias

        return {
            "ok": resultado.ok,
            "status": resultado.status,
            "mensagem": resultado.mensagem,
            "evidencias": resultado.evidencias,
            "itens": resultado.itens,
            "total": len(resultado.itens),
            "sucessos": sum(1 for item in resultado.itens if item.get("ok")),
            "erros": sum(1 for item in resultado.itens if not item.get("ok")),
        }
