"""Acesso ao SQLite (Módulo: Banco local)."""
from __future__ import annotations
import json
import sqlite3
from pathlib import Path
from typing import Optional

from core.config.settings import settings
from core.models.models import Condominio, Lancamento

SCHEMA = Path(__file__).with_name("schema.sql")


class Repository:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(db_path) if db_path else settings.db_file
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.executescript(SCHEMA.read_text(encoding="utf-8"))
        self.conn.commit()

    # ---- condomínios ----
    def upsert_condominio(self, c: Condominio) -> int:
        cur = self.conn.execute(
            "INSERT INTO condominios (nome_pasta, nome_almah, ativo) VALUES (?,?,?)",
            (c.nome_pasta, c.nome_almah, int(c.ativo)),
        )
        self.conn.commit()
        return cur.lastrowid

    def condominio_por_pasta(self, nome_pasta: str) -> Optional[Condominio]:
        row = self.conn.execute(
            "SELECT * FROM condominios WHERE nome_pasta = ?", (nome_pasta,)
        ).fetchone()
        if not row:
            return None
        return Condominio(id=row["id"], nome_pasta=row["nome_pasta"],
                          nome_almah=row["nome_almah"], ativo=bool(row["ativo"]))

    # ---- lançamentos ----
    def existe_duplicidade(self, l: Lancamento) -> bool:
        """R6: bloqueia se já houver lançamento com a mesma chave."""
        row = self.conn.execute(
            "SELECT 1 FROM lancamentos WHERE chave_dup = ? AND status != 'erro' LIMIT 1",
            (l.chave_duplicidade(),),
        ).fetchone()
        return row is not None

    def salvar_lancamento(self, l: Lancamento) -> int:
        cur = self.conn.execute(
            """INSERT INTO lancamentos
               (condominio, competencia, fornecedor, descricao, valor_liquido,
                vencimento, status, arquivos, observacao, chave_dup)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (l.condominio, l.competencia, l.fornecedor, l.descricao, l.valor_liquido,
             l.vencimento.isoformat() if l.vencimento else None,
             l.status.value, json.dumps(l.arquivos), l.observacao, l.chave_duplicidade()),
        )
        self.conn.commit()
        return cur.lastrowid

    def registrar_log(self, nivel: str, mensagem: str, etapa: str = "") -> None:
        self.conn.execute(
            "INSERT INTO logs (nivel, etapa, mensagem) VALUES (?,?,?)",
            (nivel, etapa, mensagem),
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()
