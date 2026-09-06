import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from api.services import resolver_dry_run
from core.logging.logger import criar_pasta_lancamento


class EvidenciasConfigTests(unittest.TestCase):
    def test_pasta_separada_por_lancamento(self):
        with tempfile.TemporaryDirectory() as temp:
            pasta = criar_pasta_lancamento(
                Path(temp),
                2,
                "CLARO NXT TELECOMUNICACOES S/A",
                "REF. 04/2026",
            )

            self.assertTrue(pasta.is_dir())
            self.assertTrue(pasta.name.startswith("02_CLARO_NXT_TELECOMUNICACOES_S_A"))
            self.assertIn("REF_04_2026", pasta.name)

    def test_env_controla_dry_run(self):
        with patch("api.services.settings.dry_run", True):
            self.assertTrue(resolver_dry_run(None))
        with patch("api.services.settings.dry_run", False):
            self.assertFalse(resolver_dry_run(None))

    def test_confirmacao_explicita_sobrescreve_env(self):
        with patch("api.services.settings.dry_run", True):
            self.assertFalse(resolver_dry_run(True))


if __name__ == "__main__":
    unittest.main()
