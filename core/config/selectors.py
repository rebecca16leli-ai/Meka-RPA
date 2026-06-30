"""Carregamento e resolução dos seletores centrais (Módulo 8).

Resolve um seletor pelo caminho pontilhado (ex.: 'condominio.botao_trocar') e
devolve a primeira opção utilizável. Se o seletor ainda for um placeholder TODO,
lança erro claro — protege contra rodar um passo sem o seletor real.
"""
from __future__ import annotations
from pathlib import Path
import yaml

_YAML = Path(__file__).resolve().parents[1] / "config" / "selectors.yaml"


class SeletorIndisponivelError(RuntimeError):
    pass


class Selectors:
    def __init__(self, caminho: Path = _YAML):
        self._data = yaml.safe_load(caminho.read_text(encoding="utf-8"))

    def _node(self, dotted: str) -> dict:
        no = self._data
        for parte in dotted.split("."):
            no = no[parte]
        return no

    def chain(self, dotted: str) -> list[str]:
        """Lista de seletores (ordem de fallback). Bloqueia placeholders TODO."""
        no = self._node(dotted)
        seletores = no.get("selectors", [])
        usaveis = [s for s in seletores if not str(s).startswith("TODO")]
        if not usaveis:
            nota = no.get("nota", "")
            raise SeletorIndisponivelError(
                f"Seletor '{dotted}' ainda não foi coletado (status={no.get('status')}). {nota}"
            )
        return usaveis

    def status(self, dotted: str) -> str:
        return self._node(dotted).get("status", "desconhecido")
