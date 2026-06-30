from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
URL_UI = "http://127.0.0.1:5000/ui"


def abrir_navegador(url: str) -> None:
    try:
        if os.name == "nt":
            os.startfile(url)
        else:
            subprocess.Popen(["xdg-open", url])
    except Exception:
        pass


def iniciar_servidor() -> subprocess.Popen:
    env = os.environ.copy()
    env.setdefault("PYTHONPATH", str(ROOT))
    return subprocess.Popen(
        [sys.executable, "app.py"],
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == "nt" else 0,
    )


def monitor_login(servidor: subprocess.Popen) -> None:
    while servidor.poll() is None:
        time.sleep(900)
        if servidor.poll() is not None:
            break
        print("Reabrindo fluxo de login para renovar a sessão...")
        try:
            subprocess.run([sys.executable, "-m", "automation.login"], cwd=str(ROOT), check=False)
            abrir_navegador(URL_UI)
        except Exception:
            pass


def main() -> None:
    print("Iniciando servidor local...")
    servidor = iniciar_servidor()
    time.sleep(3)
    abrir_navegador(URL_UI)

    print("Abrindo tela de login...")
    try:
        subprocess.run([sys.executable, "-m", "automation.login"], cwd=str(ROOT), check=False)
        abrir_navegador(URL_UI)
    except KeyboardInterrupt:
        pass

    thread = threading.Thread(target=monitor_login, args=(servidor,), daemon=True)
    thread.start()

    if servidor.poll() is None:
        print("Servidor continua em execução. Feche esta janela para encerrar.")
        try:
            while servidor.poll() is None:
                time.sleep(1)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
