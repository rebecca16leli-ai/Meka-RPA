import unittest

from automation.pages.lancamento_page import LancamentoPage


class FakeAbrir:
    def __init__(self):
        self.valor = "Nao"

    @property
    def first(self):
        return self

    def count(self):
        return 1

    def scroll_into_view_if_needed(self):
        pass

    def click(self):
        pass

    def text_content(self):
        return self.valor


class FakeOpcao:
    def __init__(self, texto, abrir):
        self.texto = texto
        self.abrir = abrir

    def text_content(self):
        return self.texto

    def click(self):
        self.abrir.valor = f"×{self.texto}"


class FakeOpcoes:
    def __init__(self, itens):
        self.itens = itens

    def count(self):
        return len(self.itens)

    def nth(self, indice):
        return self.itens[indice]


class FakePage:
    def __init__(self):
        self.abrir = FakeAbrir()
        self.opcoes = FakeOpcoes([
            FakeOpcao("Nao", self.abrir),
            FakeOpcao("Sim", self.abrir),
        ])

    def locator(self, seletor):
        if seletor == "fake-cobranca":
            return self.abrir
        return self.opcoes

    def wait_for_selector(self, seletor, timeout=None):
        pass


class FakeSelectors:
    def chain(self, dotted):
        self.dotted = dotted
        return ["fake-cobranca"]


class CobrancaRecebidaTests(unittest.TestCase):
    def test_define_cobranca_recebida_como_sim(self):
        page = FakePage()
        selectors = FakeSelectors()

        LancamentoPage(page, selectors).set_cobranca_recebida_sim()

        self.assertEqual(page.abrir.valor, "×Sim")
        self.assertEqual(selectors.dotted, "formulario.cobranca_recebida")


if __name__ == "__main__":
    unittest.main()
