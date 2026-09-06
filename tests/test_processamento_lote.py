import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from api.routes import _resumo_lote
from automation.flow import ResultadoLancamento, executar_lancamento


class _PaginaFake:
    def screenshot(self, **kwargs):
        return None


class _EstabelecimentoFake:
    def __init__(self, *args):
        pass

    def esta_na_tela(self):
        return False


class _CondominioFake:
    def __init__(self, *args):
        pass

    def validar_ativo(self, *args, **kwargs):
        return None


class _ContasFake:
    aberturas = 0

    def __init__(self, *args):
        pass

    def abrir(self):
        type(self).aberturas += 1


class ProcessamentoLoteTests(unittest.TestCase):
    def test_continua_apos_erro_e_retorna_resultado_por_item(self):
        documentos = [
            {"fornecedor_nome": "Fornecedor A", "competencia": "01/2026"},
            {"fornecedor_nome": "Fornecedor B", "competencia": "02/2026"},
            {"fornecedor_nome": "Fornecedor C", "competencia": "03/2026"},
        ]
        _ContasFake.aberturas = 0

        with tempfile.TemporaryDirectory() as tmp, patch(
            "automation.flow.EstabelecimentoPage", _EstabelecimentoFake
        ), patch(
            "automation.flow.CondominioPage", _CondominioFake
        ), patch(
            "automation.flow.ContasAPagarPage", _ContasFake
        ), patch(
            "automation.flow._executar_documento",
            side_effect=[
                None,
                RuntimeError("campo nao encontrado"),
                ResultadoLancamento(False, "revisao", "matricula ausente"),
            ],
        ):
            resultado = executar_lancamento(
                _PaginaFake(),
                object(),
                object(),
                {"documentos": documentos},
                "CONDOMINIO TESTE",
                pasta_execucao=Path(tmp),
            )

        self.assertEqual(_ContasFake.aberturas, 3)
        self.assertEqual([item["ok"] for item in resultado.itens], [True, False, False])
        self.assertEqual(resultado.status, "parcial")
        self.assertIn("1 sucesso(s) e 2 erro(s)", resultado.mensagem)

    def test_resumo_lote_mantem_sucessos_e_erros(self):
        resumo = _resumo_lote([{"ok": True}, {"ok": False}])

        self.assertEqual(resumo["total"], 2)
        self.assertEqual(resumo["sucessos"], 1)
        self.assertEqual(resumo["erros"], 1)
        self.assertEqual(resumo["status"], "parcial")


if __name__ == "__main__":
    unittest.main()
