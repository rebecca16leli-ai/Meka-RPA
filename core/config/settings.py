"""Configurações centrais do projeto."""

import sys
from shutil import copy2
from os import environ
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


# ======================================================================
# Diretório da aplicação
# ======================================================================

if getattr(sys, "frozen", False):
    # Rodando pelo PyInstaller
    BASE_DIR = Path(sys.executable).parent
    RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", BASE_DIR))
else:
    # Desenvolvimento
    BASE_DIR = Path(__file__).resolve().parents[2]
    RESOURCE_DIR = BASE_DIR


# ======================================================================
# Arquivo .env
# ======================================================================

ENV_FILE = BASE_DIR / ".env"


# ======================================================================
# Diretórios da aplicação
# ======================================================================

USER_DATA_DIR = Path(environ["LOCALAPPDATA"]) / "Meka RPA"
DATA_DIR = USER_DATA_DIR / "data"
INSTANCE_DIR = USER_DATA_DIR / "instance"
EVIDENCE_DIR = USER_DATA_DIR / "evidence"
TEMPLATE_DIR = RESOURCE_DIR / "templates"
STATIC_DIR = RESOURCE_DIR / "static"
ENV_FILES = (ENV_FILE, USER_DATA_DIR / ".env")


DATA_DIR.mkdir(parents=True, exist_ok=True)
USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)


# ======================================================================
# Banco
# ======================================================================

DB_FILE = INSTANCE_DIR / "data.db"
SEED_DB_FILE = RESOURCE_DIR / "instance" / "data.db"

if not DB_FILE.exists() and SEED_DB_FILE.exists():
    copy2(SEED_DB_FILE, DB_FILE)


# ======================================================================
# Configurações
# ======================================================================

class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=ENV_FILES,
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )


    # ==================================================================
    # Secrets
    # ==================================================================

    openai_api_key: str = ""
    secret_key: str = "meka-rpa-local"
    almah_usuario: str = ""
    almah_senha: str = ""


    # ==================================================================
    # Aplicação
    # ==================================================================

    almah_base_url: str = (
        "https://guerreirocondominios.almahcondos.com.br"
    )

    headless: bool = False
    dry_run: bool = True
    # Pausa entre operacoes Playwright para permitir acompanhamento visual e
    # identificar com clareza a etapa em que o portal falhou.
    slow_mo_ms: int = 2000
    default_timeout_ms: int = 30000
    login_timeout_ms: int = 45000

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
    def data_dir(self) -> Path:
        return DATA_DIR


    @property
    def chrome_path(self) -> str:
        candidates = [
            Path(environ.get("PROGRAMFILES", "")) / "Google/Chrome/Application/chrome.exe",
            Path(environ.get("PROGRAMFILES(X86)", "")) / "Google/Chrome/Application/chrome.exe",
            Path(environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe",
        ]
        chrome = next((path for path in candidates if path.exists()), None)
        if chrome is None:
            raise FileNotFoundError("Google Chrome nao encontrado.")
        return str(chrome)


    @property
    def db_file(self) -> Path:
        return DB_FILE


    @property
    def evidence_path(self) -> Path:
        return EVIDENCE_DIR


    @property
    def template_dir(self) -> Path:
        return TEMPLATE_DIR


    @property
    def static_dir(self) -> Path:
        return STATIC_DIR


settings = Settings()
