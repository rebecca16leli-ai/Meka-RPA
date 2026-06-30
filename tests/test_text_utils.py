"""Testes da normalização de nomes (base da validação R1) — não precisa de browser."""
from core.domain.text_utils import normalizar, nomes_equivalentes


def test_normalizar_remove_acentos_e_caixa():
    assert normalizar("  Condomínio   Jardim ÁGUA ") == "condominio jardim agua"


def test_equivalencia_com_variacoes():
    assert nomes_equivalentes("ART GÁS", "art gas")
    assert nomes_equivalentes("Residencial  Bela Vista", "RESIDENCIAL BELA VISTA")


def test_nao_equivalentes():
    assert not nomes_equivalentes("Condomínio A", "Condomínio B")
    assert not nomes_equivalentes("", "Condomínio A")
