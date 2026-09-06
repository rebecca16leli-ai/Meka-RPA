from __future__ import annotations

from os import system
from threading import Thread
from time import sleep

from playwright.sync_api import sync_playwright
from requests import RequestException, get
from werkzeug.serving import make_server

from app import app
from core.config.settings import settings
from core.logging.logger import get_logger

system("title Meka - Lancamentos Almah")
log = get_logger("app")


class FlaskServer(Thread):
    def __init__(self, flask_app):
        super().__init__(daemon=True)
        self.server = make_server("127.0.0.1", 5000, flask_app, threaded=True)

    def run(self) -> None:
        self.server.serve_forever()

    def stop(self) -> None:
        self.server.shutdown()


def main() -> None:
    server = FlaskServer(app)
    server.start()

    try:
        while True:
            try:
                get("http://127.0.0.1:5000", timeout=2).raise_for_status()
                break
            except RequestException:
                sleep(0.2)

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                executable_path=settings.chrome_path,
                headless=False,
            )
            context = browser.new_context()
            ui_page = context.new_page()
            ui_page.goto("http://127.0.0.1:5000", wait_until="domcontentloaded")
            log.info("Interface iniciada. O login no Almah sera feito a cada processamento.")
            ui_page.wait_for_event("close", timeout=0)
            context.close()
            browser.close()
    finally:
        server.stop()
        server.join()


if __name__ == "__main__":
    main()
