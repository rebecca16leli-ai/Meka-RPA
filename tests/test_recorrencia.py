import unittest

from automation.pages.contas_pagar_page import (
    ContasAPagarPage,
    documento_do_lancamento,
    extrair_mes_ano,
    fornecedor_e_copel,
    fornecedor_e_sanepar,
    fornecedor_usa_matricula,
    matricula_numerica,
    matricula_sanepar,
    termo_busca_recorrencia,
    ultimos_quatro_matricula,
)


class FakeLocator:
    def __init__(self, items=None, text=""):
        self.items = items
        self.text = text

    @property
    def first(self):
        return self

    def count(self):
        return len(self.items) if self.items is not None else 1

    def nth(self, index):
        return self.items[index]

    def text_content(self):
        if self.items is not None:
            return " ".join(item.text_content() or "" for item in self.items)
        return self.text

    def locator(self, selector):
        if selector == "td":
            return FakeLocator(self.items)
        if selector == "tbody tr":
            return self.rows
        if selector == "thead th":
            return self.headers
        raise AssertionError(selector)


class FakeTable(FakeLocator):
    def __init__(self, headers, rows):
        super().__init__()
        self.headers = FakeLocator([FakeLocator(text=item) for item in headers])
        self.rows = FakeLocator([
            FakeLocator([FakeLocator(text=cell) for cell in row])
            for row in rows
        ])


class FakePage:
    def __init__(self, table):
        self.table = table

    def locator(self, selector):
        assert selector == "table.dataTable"
        return self.table


class RegraRecorrenciaTests(unittest.TestCase):
    def test_copel_e_sanepar_usam_matricula(self):
        self.assertTrue(fornecedor_usa_matricula("COPEL DISTRIBUICAO S.A."))
        self.assertTrue(fornecedor_usa_matricula("Companhia de Saneamento SANEPAR"))
        self.assertFalse(fornecedor_usa_matricula("CLARO NXT TELECOMUNICACOES S/A"))

    def test_copel_busca_pelos_quatro_ultimos_digitos(self):
        self.assertTrue(fornecedor_e_copel("COPEL DISTRIBUICAO S.A."))
        self.assertEqual(ultimos_quatro_matricula("4835760"), "5760")
        self.assertEqual(
            termo_busca_recorrencia("COPEL DISTRIBUICAO S.A.", "4835760"),
            "5760",
        )
        self.assertEqual(
            documento_do_lancamento(
                "COPEL DISTRIBUICAO S.A.",
                "4835760",
                "REF. 07/2026",
            ),
            "4835760",
        )

    def test_outro_fornecedor_continua_buscando_pelo_nome(self):
        self.assertEqual(
            termo_busca_recorrencia("CLARO NXT TELECOMUNICACOES S/A", None),
            "CLARO NXT TELECOMUNICACOES S/A",
        )

    def test_sanepar_busca_pela_matricula_completa(self):
        self.assertTrue(fornecedor_e_sanepar("COMPANHIA DE SANEAMENTO SANEPAR"))
        self.assertEqual(matricula_numerica("12.345.678-9"), "123456789")
        self.assertEqual(matricula_sanepar("12.345.678-9"), "12.345.678-9")
        self.assertEqual(
            termo_busca_recorrencia("COMPANHIA DE SANEAMENTO SANEPAR", "12.345.678-9"),
            "12.345.678-9",
        )
        self.assertEqual(
            documento_do_lancamento(
                "COMPANHIA DE SANEAMENTO SANEPAR",
                "12.345.678-9",
                "REF. 07/2026",
            ),
            "12.345.678-9",
        )

    def test_fornecedor_comum_mantem_documento_referencia(self):
        self.assertEqual(
            documento_do_lancamento("CLARO NXT", None, "REF. 07/2026"),
            "REF. 07/2026",
        )

    def test_extrai_referencia_do_boleto(self):
        self.assertEqual(extrair_mes_ano("REF. 04/2026", "03/2026"), "04/2026")

    def test_competencia_e_fallback_da_referencia(self):
        self.assertEqual(extrair_mes_ano(None, "05/2026"), "05/2026")

    def test_claro_desempata_pela_referencia(self):
        tabela = FakeTable(
            ["Doc", "Vencimento"],
            [
                ["REF. 03/2026", "10/04/2026"],
                ["REF. 04/2026", "10/05/2026"],
            ],
        )
        pagina = ContasAPagarPage(FakePage(tabela), None)

        escolhida = pagina.selecionar_recorrencia(
            fornecedor_nome="CLARO NXT TELECOMUNICACOES S/A",
            documento_referencia="REF. 04/2026",
            competencia="04/2026",
        )

        self.assertIn("REF. 04/2026", escolhida.text_content())

    def test_copel_desempata_pela_matricula(self):
        tabela = FakeTable(
            ["Doc", "Vencimento"],
            [
                ["111111", "10/04/2026"],
                ["4835760", "10/05/2026"],
            ],
        )
        pagina = ContasAPagarPage(FakePage(tabela), None)

        escolhida = pagina.selecionar_recorrencia(
            fornecedor_nome="COPEL DISTRIBUICAO S.A.",
            filtro="4835760",
            documento_referencia="REF. 04/2026",
        )

        self.assertIn("4835760", escolhida.text_content())

    def test_sanepar_desempata_pela_matricula_completa(self):
        tabela = FakeTable(
            ["Doc", "Vencimento"],
            [
                ["123.456.789", "10/04/2026"],
                ["987.654.321", "10/05/2026"],
            ],
        )
        pagina = ContasAPagarPage(FakePage(tabela), None)

        escolhida = pagina.selecionar_recorrencia(
            fornecedor_nome="COMPANHIA DE SANEAMENTO SANEPAR",
            filtro="123.456.789",
            documento_referencia="REF. 04/2026",
        )

        self.assertIn("123.456.789", escolhida.text_content())


if __name__ == "__main__":
    unittest.main()
