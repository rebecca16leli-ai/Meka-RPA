"""Adapter de navegador (Módulo 5).

- Reaproveita a sessão criada manualmente em login.py via storage_state.
- Anexa um interceptador de respostas XHR para servir de SEGUNDO sinal de
  verificação (ex.: confirmar qual condomínio o backend reconheceu na troca).
  Se as substrings de URL não estiverem configuradas no .env, opera só por DOM.
"""
from __future__ import annotations
from contextlib import contextmanager
from typing import Iterator

from playwright.sync_api import sync_playwright, Page, Response

from core.config.settings import settings
from core.logging.logger import get_logger

log = get_logger("browser")


class SessaoInvalidaError(RuntimeError):
    pass


class XHRBuffer:
    """Guarda as últimas respostas XHR relevantes, por categoria."""
    def __init__(self) -> None:
        self.ultimas: dict[str, dict] = {}

    def registrar(self, categoria: str, url: str, status: int, corpo: str | None) -> None:
        self.ultimas[categoria] = {"url": url, "status": status, "corpo": corpo}

    def ultima(self, categoria: str) -> dict | None:
        return self.ultimas.get(categoria)


class BrowserManager:
    def __init__(self) -> None:
        self.xhr = XHRBuffer()

    @contextmanager
    def pagina(self) -> Iterator[Page]:
        if not settings.auth_state_file.exists():
            raise SessaoInvalidaError(
                "Sessão não encontrada. Rode primeiro: python -m automation.login"
            )
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=settings.headless, slow_mo=settings.slow_mo_ms)
            context = browser.new_context(storage_state=str(settings.auth_state_file))
            context.set_default_timeout(settings.default_timeout_ms)
            page = context.new_page()
            self._anexar_interceptador(page)
            try:
                yield page
            finally:
                context.close()
                browser.close()

    def _anexar_interceptador(self, page: Page) -> None:
        troca = settings.xhr_troca_condominio.strip()
        salvar = settings.xhr_salvar_lancamento.strip()

        def on_response(resp: Response) -> None:
            url = resp.url
            try:
                if troca and troca in url:
                    self.xhr.registrar("troca_condominio", url, resp.status, self._corpo(resp))
                elif salvar and salvar in url:
                    self.xhr.registrar("salvar_lancamento", url, resp.status, self._corpo(resp))
            except Exception as e:  # nunca derruba o fluxo por causa de log
                log.debug("Falha ao ler resposta XHR: %s", e)

        page.on("response", on_response)

    @staticmethod
    def _corpo(resp: Response) -> str | None:
        ctype = resp.headers.get("content-type", "")
        if "json" in ctype or "text" in ctype:
            try:
                return resp.text()
            except Exception:
                return None
        return None

    def sessao_ativa(self, page: Page, seletor_login: list[str]) -> bool:
        """True se NÃO estamos na tela de login (R7)."""
        for sel in seletor_login:
            if page.locator(sel).count() > 0 and page.locator(sel).first.is_visible():
                return False
        return True

    def esta_logado(self, page: Page, selectors) -> bool:
        """Logado se caímos na tela de ENTRADA (estabelecimento) ou na PRINCIPAL.
        Robusto: não dá falso 'expirada' na tela de entrada (que não tem senha)."""
        if "estabelecimento" in (page.url or "").lower():
            return True
        for dotted in ("estabelecimento.select2_abrir", "condominio.nome_ativo"):
            try:
                loc = page.locator(selectors.chain(dotted)[0]).first
                if loc.count() > 0 and loc.is_visible():
                    return True
            except Exception:
                pass
        return False
