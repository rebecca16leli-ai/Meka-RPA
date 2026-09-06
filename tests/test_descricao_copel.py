import unittest

from core.domain.competencia import (
    formatar_consumo_kwh,
    montar_descricao_copel,
    montar_descricao_sanepar,
)


class DescricaoCopelTests(unittest.TestCase):
    def test_monta_descricao_com_referencia_e_consumo(self):
        self.assertEqual(
            montar_descricao_copel(
                "COPEL GERAL REF. 06/2026 - 3500 KWH",
                "07/2026",
                3642,
            ),
            "COPEL GERAL REF. 07/2026 - 3642 KWH",
        )

    def test_usa_nome_padrao_quando_recorrencia_tem_so_referencia(self):
        self.assertEqual(
            montar_descricao_copel("REF. 06/2026", "07/2026", 3642),
            "COPEL GERAL REF. 07/2026 - 3642 KWH",
        )

    def test_remove_zeros_decimais_desnecessarios(self):
        self.assertEqual(formatar_consumo_kwh(3642.0), "3642")

    def test_rejeita_consumo_ausente(self):
        with self.assertRaises(ValueError):
            formatar_consumo_kwh(None)

    def test_monta_descricao_sanepar_com_consumo_em_metros_cubicos(self):
        self.assertEqual(
            montar_descricao_sanepar(
                "SANEPAR GERAL REF. 06/2026 - 18 M³",
                "07/2026",
                22,
            ),
            "SANEPAR GERAL REF. 07/2026 - 22 M³",
        )


if __name__ == "__main__":
    unittest.main()
