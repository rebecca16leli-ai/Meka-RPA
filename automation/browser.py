"""Gerencia um contexto Playwright isolado para cada processamento."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from playwright.sync_api import Page, Response, sync_playwright

from core.config.settings import settings
from core.logging.logger import get_logger

log = get_logger("browser")


class SessaoInvalidaError(RuntimeError):
    """Mantida por compatibilidade com entradas CLI antigas."""


class XHRBuffer:
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
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                executable_path=settings.chrome_path,
                headless=settings.headless,
                slow_mo=settings.slow_mo_ms,
            )
            context = browser.new_context()
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
            try:
                if troca and troca in resp.url:
                    self.xhr.registrar("troca_condominio", resp.url, resp.status, self._corpo(resp))
                elif salvar and salvar in resp.url:
                    self.xhr.registrar("salvar_lancamento", resp.url, resp.status, self._corpo(resp))
            except Exception as exc:
                log.debug("Falha ao ler resposta XHR: %s", exc)

        page.on("response", on_response)

    @staticmethod
    def _corpo(resp: Response) -> str | None:
        ctype = resp.headers.get("content-type", "")
        if "json" not in ctype and "text" not in ctype:
            return None
        try:
            return resp.text()
        except Exception:
            return None

    def sessao_ativa(self, page: Page, seletor_login: list[str]) -> bool:
        return not any(
            page.locator(sel).count() > 0 and page.locator(sel).first.is_visible()
            for sel in seletor_login
        )

    def esta_logado(self, page: Page, selectors) -> bool:
        if "estabelecimento" in (page.url or "").lower():
            return True
        for dotted in ("estabelecimento.select2_abrir", "condominio.nome_ativo"):
            try:
                loc = page.locator(selectors.chain(dotted)[0]).first
                if loc.count() > 0 and loc.is_visible():
                    return True
            except Exception:
                continue
        return False
