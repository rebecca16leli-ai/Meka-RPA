"""Normalização de texto para comparações robustas de nomes."""
import re
import unicodedata


def normalizar(texto: str | None) -> str:
    """Remove acentos, baixa caixa, colapsa espaços. Para comparar nomes de
    condomínio entre o que está na tela e o nome esperado da tabela."""
    if not texto:
        return ""
    t = unicodedata.normalize("NFKD", texto)
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"\s+", " ", t).strip().lower()
    return t


def nomes_equivalentes(a: str | None, b: str | None) -> bool:
    return normalizar(a) == normalizar(b)
