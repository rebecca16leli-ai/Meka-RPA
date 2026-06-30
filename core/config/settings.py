"""Configurações centrais do projeto (lê variáveis do .env)."""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    almah_base_url: str = "https://SEU_ALMAH_AQUI"
    auth_state_path: str = "data/auth_state.json"
    db_path: str = "data/almah.db"

    headless: bool = False
    slow_mo_ms: int = 0
    default_timeout_ms: int = 15000

    evidence_dir: str = "evidence"

    # Substrings de URL para verificação por XHR (opcionais — vazio = só DOM)
    xhr_troca_condominio: str = ""
    xhr_salvar_lancamento: str = ""

    # ---- caminhos absolutos resolvidos a partir da raiz do projeto ----
    @property
    def auth_state_file(self) -> Path:
        return ROOT / self.auth_state_path

    @property
    def db_file(self) -> Path:
        return ROOT / self.db_path

    @property
    def evidence_path(self) -> Path:
        return ROOT / self.evidence_dir


settings = Settings()
