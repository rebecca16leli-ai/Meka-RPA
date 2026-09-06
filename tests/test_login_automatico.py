import unittest
from unittest.mock import patch

from automation.pages.login_page import CredenciaisAusentesError, LoginPage


class LoginAutomaticoTests(unittest.TestCase):
    def test_falha_antes_de_abrir_portal_sem_credenciais(self):
        with (
            patch("automation.pages.login_page.settings.almah_usuario", ""),
            patch("automation.pages.login_page.settings.almah_senha", ""),
        ):
            with self.assertRaisesRegex(CredenciaisAusentesError, "ALMAH_USUARIO"):
                LoginPage(object()).autenticar()


if __name__ == "__main__":
    unittest.main()
