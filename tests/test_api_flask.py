import unittest
from unittest.mock import patch

from app import app
from api.routes import _extrair_documentos_sem_agrupar_utilidades, _nome_fornecedor


class ApiFlaskTests(unittest.TestCase):
    def test_normaliza_nome_copel_com_sufixo_de_copia(self):
        self.assertEqual(_nome_fornecedor("FATURA_-_COPEL_2.pdf"), "COPEL")

    def test_normaliza_nome_com_prefixo_de_documento(self):
        self.assertEqual(_nome_fornecedor("BOLETO - ARTGAZ.pdf"), "ARTGAZ")

    def test_copel_e_sanepar_sao_extraidas_um_arquivo_por_vez(self):
        dados = [
            {"fornecedor": "ARTGAZ", "arquivo": "artgaz.pdf"},
            {"fornecedor": "CLARO", "arquivo": "claro.pdf"},
            {"fornecedor": "COPEL DISTRIBUICAO", "arquivo": "copel_1.pdf"},
            {"fornecedor": "COPEL DISTRIBUICAO", "arquivo": "copel_2.pdf"},
            {"fornecedor": "SANEPAR", "arquivo": "sanepar.pdf"},
        ]

        def resposta(itens):
            return {
                "documentos": [
                    {"anexos": [item["arquivo"]]}
                    for item in itens
                ]
            }

        with patch("api.routes.ler_documento", side_effect=resposta) as extrair:
            resultado = _extrair_documentos_sem_agrupar_utilidades(dados)

        self.assertEqual([len(chamada.args[0]) for chamada in extrair.call_args_list], [2, 1, 1, 1])
        self.assertEqual(len(resultado["documentos"]), 5)

    def test_root_endpoint_returns_status_message(self):
        client = app.test_client()
        response = client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Meka RPA", response.data)
        self.assertIn(b"GRAVA", response.data)
        self.assertIn(b"resultadoAccordion", response.data)
        self.assertIn(b"Resultado do lote", response.data)

    def test_condominios_route_returns_csv_entries(self):
        client = app.test_client()
        response = client.get("/condominios")

        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.get_json()), 1)
        self.assertIn("nome", response.get_json()[0])

    def test_processar_rejeita_condominio_ausente(self):
        client = app.test_client()
        response = client.post("/processar", data={})

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.get_json()["ok"])


if __name__ == "__main__":
    unittest.main()
