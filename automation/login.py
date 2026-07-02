from __future__ import annotations
from time import sleep
from playwright.sync_api import sync_playwright
from core.config.settings import settings
from core.logging.logger import get_logger
from subprocess import call
from threading import Thread

log = get_logger("login")

def main() -> None:
    settings.auth_state_file.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto(settings.almah_base_url)

        print("\n==============================================================")
        print(" Faça LOGIN manualmente na janela do navegador que abriu.")
        print(" Quando o sistema estiver aberto e logado, volte aqui e")
        print(" pressione ENTER para gravar a sessão.")
        print("==============================================================\n")
        input(" >> Pressione ENTER após concluir o login... ")

        context.storage_state(path=str(settings.auth_state_file))
        log.info("Sessão gravada em %s", settings.auth_state_file)
        context.close()
    
        def runing(): return call("python -m app", shell=True)

        Thread(target=runing, daemon=True).start()

        sleep(3)
        context = browser.new_context()
        page = context.new_page()
        page.goto("http://localhost:5000")
        input("Ao finalizar os lançamentos fecha aqui pressionando ENTER.")
        browser.close()

if __name__ == "__main__": main()
