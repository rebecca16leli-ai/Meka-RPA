"""Autenticacao no Almah com credenciais do arquivo .env."""
from __future__ import annotations

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from core.config.settings import settings
from core.logging.logger import get_logger

log = get_logger("login")


class CredenciaisAusentesError(RuntimeError):
    pass


class LoginError(RuntimeError):
    pass


class LoginPage:
    USUARIO = "#f_login"
    SENHA = "#f_senha"
    ENTRAR = "#btn"
    ERROS = ".alert-danger, .toast-message, .swal2-html-container, .help-block"

    def __init__(self, page: Page):
        self.page = page

    def autenticar(self) -> None:
        usuario = settings.almah_usuario.strip()
        senha = settings.almah_senha
        if not usuario or not senha:
            raise CredenciaisAusentesError(
                "Configure ALMAH_USUARIO e ALMAH_SENHA no arquivo .env."
            )

        self.page.goto(settings.almah_base_url, wait_until="domcontentloaded")
        campo_senha = self.page.locator(self.SENHA)

        if campo_senha.count() == 0 or not campo_senha.first.is_visible():
            log.info("Portal abriu em sessao autenticada.")
            return

        log.info("Autenticando no Almah com o usuario configurado no .env.")
        self.page.locator(self.USUARIO).fill(usuario)
        campo_senha.fill(senha)
        self.page.locator(self.ENTRAR).click()

        try:
            campo_senha.wait_for(state="hidden", timeout=settings.login_timeout_ms)
            self.page.wait_for_load_state("domcontentloaded")
        except PlaywrightTimeoutError as exc:
            detalhe = self._mensagem_erro()
            raise LoginError(
                detalhe or "O Almah nao concluiu o login. Confira usuario, senha e acesso ao portal."
            ) from exc

        if campo_senha.count() and campo_senha.first.is_visible():
            raise LoginError(self._mensagem_erro() or "O Almah permaneceu na tela de login.")

        log.info("Login concluido; continuando no mesmo contexto do navegador.")

    def _mensagem_erro(self) -> str:
        erros = self.page.locator(self.ERROS)
        for i in range(erros.count()):
            item = erros.nth(i)
            try:
                if item.is_visible():
                    texto = (item.text_content() or "").strip()
                    if texto:
                        return texto
            except Exception:
                continue
        return ""
