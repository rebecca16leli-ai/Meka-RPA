"""Configurações centrais do projeto."""

import sys
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


# ======================================================================
# Diretório da aplicação
# ======================================================================

if getattr(sys, "frozen", False):
    # Rodando pelo PyInstaller
    BASE_DIR = Path(sys.executable).parent
else:
    # Desenvolvimento
    BASE_DIR = Path(__file__).resolve().parents[2]


# ======================================================================
# Arquivo .env
# ======================================================================

ENV_FILE = BASE_DIR / ".env"


# ======================================================================
# Diretórios da aplicação
# ======================================================================

DATA_DIR = BASE_DIR / "data"
INSTANCE_DIR = BASE_DIR / "instance"
EVIDENCE_DIR = BASE_DIR / "evidence"


DATA_DIR.mkdir(parents=True, exist_ok=True)
INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)


# ======================================================================
# Banco
# ======================================================================

DB_FILE = INSTANCE_DIR / "data.db"


# ======================================================================
# Configurações
# ======================================================================

class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )


    # ==================================================================
    # Secrets
    # ==================================================================

    openai_api_key: str
    secret_key: str


    # ==================================================================
    # Aplicação
    # ==================================================================

    almah_base_url: str = (
        "https://guerreirocondominios.almahcondos.com.br"
    )

    headless: bool = False
    slow_mo_ms: int = 0
    default_timeout_ms: int = 1500000

    xhr_troca_condominio: str = ""
    xhr_salvar_lancamento: str = ""


    # ==================================================================
    # Banco
    # ==================================================================

    db_uri: str = f"sqlite:///{DB_FILE.as_posix()}"


    # ==================================================================
    # Caminhos
    # ==================================================================

    @property
    def root(self) -> Path:
        return BASE_DIR


    @property
    def auth_state_file(self) -> Path:
        return DATA_DIR / "auth_state.json"


    @property
    def db_file(self) -> Path:
        return DB_FILE


    @property
    def evidence_path(self) -> Path:
        return EVIDENCE_DIR


settings = Settings()