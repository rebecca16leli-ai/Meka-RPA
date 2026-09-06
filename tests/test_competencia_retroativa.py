import unittest

from core.domain.competencia import validar_competencia


class CompetenciaRetroativaTests(unittest.TestCase):
    def test_referencia_antiga_e_permitida(self):
        self.assertEqual(validar_competencia("01/2020"), (1, 2020))
        self.assertEqual(validar_competencia("12/2025"), (12, 2025))

    def test_formato_invalido_continua_bloqueado(self):
        with self.assertRaises(ValueError):
            validar_competencia("13/2020")


if __name__ == "__main__":
    unittest.main()
