"""Logging estruturado e captura de evidencias da automacao."""
from __future__ import annotations

import logging
import os
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

from core.config.settings import settings

_LOG_DIR = Path(os.environ["LOCALAPPDATA"]) / "Meka RPA" / "logs"
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


def nome_seguro(valor: str | None, padrao: str = "sem_referencia") -> str:
    texto = unicodedata.normalize("NFKD", str(valor or ""))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r"[^A-Za-z0-9]+", "_", texto).strip("_")
    return texto[:80] or padrao


def criar_pasta_execucao() -> Path:
    settings.evidence_path.mkdir(parents=True, exist_ok=True)
    pasta = settings.evidence_path / datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    pasta.mkdir(parents=True, exist_ok=False)
    return pasta


def criar_pasta_lancamento(
    pasta_execucao: Path,
    indice: int,
    fornecedor: str | None,
    referencia: str | None,
) -> Path:
    nome = f"{indice:02d}_{nome_seguro(fornecedor, 'fornecedor')}_{nome_seguro(referencia)}"
    pasta = pasta_execucao / nome
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def salvar_evidencia(
    page,
    etapa: str,
    ref: str | None = "geral",
    full_page: bool = True,
    pasta: Path | None = None,
) -> Path:
    destino_pasta = pasta or settings.evidence_path
    destino_pasta.mkdir(parents=True, exist_ok=True)
    nome = f"{datetime.now():%H%M%S_%f}_{nome_seguro(ref, 'geral')}_{nome_seguro(etapa, 'etapa')}.png"
    destino = destino_pasta / nome
    page.screenshot(path=str(destino), full_page=full_page)
    return destino
