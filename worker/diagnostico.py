"""Diagnóstico: mostra em que tela o Almah abre e quais elementos existem.

Não altera nada. Abre o Almah com a sessão salva, espera carregar, reporta a
URL e a presença dos seletores-chave, e salva um print em evidence/.

Uso:
    python -m worker.diagnostico
"""
from __future__ import annotations
from pathlib import Path

from automation.browser import BrowserManager
from core.config.settings import settings
from core.logging.logger import get_logger, salvar_evidencia

log = get_logger("diagnostico")

ALVOS = {
    "entrada: botão Entrar (#btn-almah)": "#btn-almah",
    "entrada: Select2 (span.select2-selection--single)": "span.select2-selection--single",
    "principal: nome do condomínio (a.hi-nome-est)": "a.hi-nome-est",
    "principal: trocar condomínio (#btn-condominio)": "#btn-condominio",
    "menu Financeiro (a.dropdown-toggle.modulo)": "a.dropdown-toggle.modulo",
    "tela de login (input senha)": "input[type='password']",
}


def main() -> None:
    browser = BrowserManager()
    with browser.pagina() as page:
        log.info("Abrindo: %s", settings.almah_base_url)
        page.goto(settings.almah_base_url)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(3000)  # dá tempo para redirecionamentos via JS

        print("\n==================== DIAGNÓSTICO ====================")
        print("URL atual :", page.url)
        print("Título    :", page.title())
        print("-----------------------------------------------------")
        for nome, sel in ALVOS.items():
            try:
                loc = page.locator(sel)
                qtd = loc.count()
                vis = loc.first.is_visible() if qtd else False
                print(f"  [{'X' if qtd else ' '}] {nome}: encontrados={qtd} visível={vis}")
            except Exception as e:
                print(f"  [?] {nome}: erro ao checar ({e})")
        print("-----------------------------------------------------")

        destino = salvar_evidencia(page, "diagnostico", "tela")
        print("Print salvo em:", destino)
        print("=====================================================\n")
        log.info("Diagnóstico concluído. Confira o print e me envie a saída acima.")


if __name__ == "__main__":
    main()
