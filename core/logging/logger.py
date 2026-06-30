"""Logging estruturado e captura de evidências (Módulo: Logs)."""
from __future__ import annotations
import logging
import sys
from datetime import datetime
from pathlib import Path

from core.config.settings import settings

_LOG_DIR = Path(__file__).resolve().parents[2] / "logs"
_LOG_DIR.mkdir(parents=True, exist_ok=True)


def get_logger(nome: str = "almah") -> logging.Logger:
    logger = logging.getLogger(nome)
    if logger.handlers:
        return logger
    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    fh = logging.FileHandler(_LOG_DIR / "execucao.log", encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    return logger


def salvar_evidencia(page, etapa: str, ref: str = "geral") -> Path:
    """Salva print da tela rotulado por etapa (R11/evidências)."""
def salvar_evidencia(page, etapa: str, ref: str = "geral", full_page: bool = True) -> Path:
    """Salva print da tela rotulado por etapa (R11/evidências)."""
    settings.evidence_path.mkdir(parents=True, exist_ok=True)
    nome = f"{datetime.now():%Y%m%d_%H%M%S}_{ref}_{etapa}.png".replace(" ", "_")
    destino = settings.evidence_path / nome
    page.screenshot(path=str(destino), full_page=full_page)
    return destino
