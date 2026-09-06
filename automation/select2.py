"""Helper para componentes Select2 (usado na Conta da grade de valor).

Padrão de uso do Select2 do Almah: clicar no container para abrir, digitar no
campo de busca que aparece, aguardar a lista e clicar na opção correspondente.
"""
from __future__ import annotations
from playwright.sync_api import Page, Locator

from core.domain.text_utils import normalizar
from core.logging.logger import get_logger

log = get_logger("select2")

SEARCH_FIELD = ".select2-container--open .select2-search__field, .select2-search__field"
OPTION = "li.select2-results__option"


class Select2Error(RuntimeError):
    pass


def escolher_opcao_fixa(
    page: Page,
    abrir: Locator,
    texto: str,
    timeout: int = 10000,
) -> None:
    """Escolhe uma opcao curta de Select2 que pode nao ter campo de busca."""
    abrir.scroll_into_view_if_needed()
    abrir.click()
    seletor_opcoes = ".select2-container--open li.select2-results__option"
    page.wait_for_selector(seletor_opcoes, timeout=timeout)

    opcoes = page.locator(seletor_opcoes)
    alvo = None
    for i in range(opcoes.count()):
        opcao = opcoes.nth(i)
        if normalizar(opcao.text_content()) == normalizar(texto):
            alvo = opcao
            break
    if alvo is None:
        raise Select2Error(f"Opcao '{texto}' nao encontrada no Select2.")
    alvo.click()
    log.info("Select2: opcao fixa selecionada '%s'", texto)


def escolher(page: Page, abrir: Locator, texto_busca: str, conter: bool = True,
             timeout: int = 10000) -> None:
    """Abre o Select2 em `abrir`, digita `texto_busca` e clica na opção.

    conter=True  -> escolhe a opção que CONTÉM o texto (ex.: buscar pelo código
                    reduzido da conta e casar a opção 'CODE - DESCRIÇÃO').
    conter=False -> exige correspondência exata do texto (normalizado).
    """
    abrir.scroll_into_view_if_needed()
    # Abre o dropdown só se ainda não estiver aberto (alguns Select2 abrem
    # sozinhos no carregamento da tela — reclicar fecharia).
    ja_aberto = (page.locator(SEARCH_FIELD).count() > 0
                 and page.locator(SEARCH_FIELD).last.is_visible())
    if not ja_aberto:
        abrir.click()
    page.wait_for_selector(SEARCH_FIELD, timeout=timeout)
    campo = page.locator(SEARCH_FIELD).last
    campo.fill(texto_busca)
    page.wait_for_selector(OPTION, timeout=timeout)

    opcoes = page.locator(OPTION)
    alvo = None
    for i in range(opcoes.count()):
        op = opcoes.nth(i)
        txt = op.text_content() or ""
        if conter:
            if normalizar(texto_busca) in normalizar(txt):
                alvo = op
                break
        else:
            if normalizar(txt) == normalizar(texto_busca):
                alvo = op
                break
    if alvo is None:
        raise Select2Error(f"Opção para '{texto_busca}' não encontrada no Select2.")
    alvo.click()
    log.info("Select2: selecionado '%s'", texto_busca)


def escolher_conta(page: Page, abrir: Locator, descricao: str, timeout: int = 10000) -> None:
    """Seleciona a Conta pela DESCRIÇÃO (ex.: 'GÁS'), ignorando o código.

    As opções vêm como 'CODIGO - DESCRIÇÃO'. Casamos a parte da descrição
    exatamente, para reusar a MESMA conta que já estava na recorrência sem
    risco de pegar uma parecida (ex.: 'GÁS' vs 'AQUISIÇÃO DE GÁS')."""
    abrir.scroll_into_view_if_needed()
    ja_aberto = (page.locator(SEARCH_FIELD).count() > 0
                 and page.locator(SEARCH_FIELD).last.is_visible())
    if not ja_aberto:
        abrir.click()
    page.wait_for_selector(SEARCH_FIELD, timeout=timeout)
    campo = page.locator(SEARCH_FIELD).last
    campo.fill(descricao)
    page.wait_for_selector(OPTION, timeout=timeout)

    opcoes = page.locator(OPTION)
    total = opcoes.count()
    alvo = None
    for i in range(total):
        op = opcoes.nth(i)
        txt = op.text_content() or ""
        desc = txt.split(" - ", 1)[-1] if " - " in txt else txt
        if normalizar(desc) == normalizar(descricao):
            alvo = op
            break
    if alvo is None and total == 1:
        alvo = opcoes.first   # única opção restante: usa ela
    if alvo is None:
        raise Select2Error(f"Conta '{descricao}' não encontrada de forma única.")
    alvo.click()
    log.info("Select2 (conta mantida): '%s'", descricao)
