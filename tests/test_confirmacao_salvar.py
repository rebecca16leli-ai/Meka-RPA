import unittest

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from automation.pages.lancamento_page import LancamentoPage


class _ListaVazia:
    def count(self):
        return 0


class _BotaoFake:
    def __init__(self, confirma):
        self.confirma = confirma
        self.clicado = False

    @property
    def first(self):
        return self

    def count(self):
        return 1

    def click(self):
        self.clicado = True

    def wait_for(self, state, timeout):
        if not self.confirma:
            raise PlaywrightTimeoutError("modal permaneceu aberto")


class _PaginaFake:
    def __init__(self, confirma):
        self.botao = _BotaoFake(confirma)

    def locator(self, seletor):
        if seletor == "#btn-salvar":
            return self.botao
        return _ListaVazia()

    def wait_for_timeout(self, tempo):
        pass


class _SeletoresFake:
    def chain(self, dotted):
        return ["#btn-salvar"]


class ConfirmacaoSalvarTests(unittest.TestCase):
    def test_sucesso_so_depois_do_formulario_fechar(self):
        pagina = _PaginaFake(confirma=True)

        LancamentoPage(pagina, _SeletoresFake()).salvar()

        self.assertTrue(pagina.botao.clicado)

    def test_formulario_aberto_retorna_falha(self):
        pagina = _PaginaFake(confirma=False)

        with self.assertRaisesRegex(RuntimeError, "nao confirmou a gravacao"):
            LancamentoPage(pagina, _SeletoresFake()).salvar()


if __name__ == "__main__":
    unittest.main()
