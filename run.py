from __future__ import annotations

from os import environ, system
from pathlib import Path
from threading import Thread
from time import sleep

from playwright.sync_api import sync_playwright
from requests import ConnectionError, get
from werkzeug.serving import make_server

from core.config.settings import settings
from core.logging.logger import get_logger
from app import app

system("title Meka - Lançamentos Almah")


# ======================================================================
# Localiza o Google Chrome
# ======================================================================

POSSIVEIS = [
    Path(environ.get("PROGRAMFILES", "")) / "Google/Chrome/Application/chrome.exe",
    Path(environ.get("PROGRAMFILES(X86)", "")) / "Google/Chrome/Application/chrome.exe",
    Path(environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe",
]

chrome = next((str(p) for p in POSSIVEIS if p.exists()), None)

if chrome is None:
    raise FileNotFoundError("Google Chrome não encontrado.")


# ======================================================================
# Flask
# ======================================================================


class FlaskServer(Thread):
    def __init__(self, app):
        super().__init__(daemon=True)
        self.server = make_server("127.0.0.1", 5000, app)
        self.ctx = app.app_context()
        self.ctx.push()

    def run(self):
        self.server.serve_forever()

    def stop(self):
        self.server.shutdown()


# ======================================================================
# Playwright
# ======================================================================

with sync_playwright() as p:
    log = get_logger("login")

    browser = p.chromium.launch(
        executable_path=chrome,
        headless=settings.headless,
    )

    # --------------------------------------------------------------
    # Carrega sessão existente ou cria uma nova
    # --------------------------------------------------------------

    if settings.auth_state_file.exists():

        log.info("Utilizando sessão salva.")

        context = browser.new_context(storage_state=str(settings.auth_state_file))

    else:

        log.info("Primeiro acesso. Faça login.")

        context = browser.new_context()

        login_page = context.new_page()

        login_page.goto(settings.almah_base_url)

        log.info("Faça o login e feche a aba quando terminar.")

        login_page.wait_for_event("close", timeout=0)

        context.storage_state(path=str(settings.auth_state_file))

        log.info("Sessão gravada em %s", settings.auth_state_file)

    # --------------------------------------------------------------
    # Inicia servidor Flask
    # --------------------------------------------------------------

    server = FlaskServer(app)
    server.start()

    while True:
        try:
            get("http://127.0.0.1:5000")
            break

        except ConnectionError:
            sleep(0.2)

    # --------------------------------------------------------------
    # Abre interface
    # --------------------------------------------------------------

    ui_page = context.new_page()

    ui_page.goto("http://127.0.0.1:5000")

    ui_page.wait_for_event("close", timeout=0)

    # --------------------------------------------------------------
    # Finalização
    # --------------------------------------------------------------

    server.stop()
    server.join()

    context.close()
    browser.close()
