"""Modelos de dados do domínio (Módulo 4)."""
from __future__ import annotations
from datetime import date
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class StatusLancamento(str, Enum):
    PENDENTE = "pendente"
    PRONTO = "pronto"
    LANCADO = "lancado"
    ERRO = "erro"
    REVISAO = "revisao"
    BLOQUEADO_DUPLICIDADE = "bloqueado_duplicidade"


class TipoDocumento(str, Enum):
    BOLETO = "boleto"
    COMPROVANTE = "comprovante"
    NOTA_FISCAL = "nota_fiscal"
    DESCONHECIDO = "desconhecido"


class Condominio(BaseModel):
    id: Optional[int] = None
    nome_pasta: str
    nome_almah: str = Field(..., description="Nome EXATO exibido no Almah — base da validação.")
    ativo: bool = True


class ResultadoExtracao(BaseModel):
    """JSON padronizado devolvido pela camada de extração (Fase 2)."""
    tipo_documento: TipoDocumento = TipoDocumento.DESCONHECIDO
    fornecedor: str = ""
    competencia: str = ""          # MM/AAAA
    valor_liquido: Optional[float] = None
    vencimento: Optional[date] = None
    descricao_sugerida: str = ""
    cnpj: str = ""
    numero_nf: str = ""
    confianca: float = 0.0         # 0..1
    origem: str = "indefinida"     # "deterministica" | "vision" | "manual"


class Lancamento(BaseModel):
    id: Optional[int] = None
    condominio: str                 # nome_almah esperado
    competencia: str
    fornecedor: str
    descricao: str = ""
    valor_liquido: Optional[float] = None
    vencimento: Optional[date] = None
    status: StatusLancamento = StatusLancamento.PENDENTE
    arquivos: list[str] = Field(default_factory=list)
    observacao: str = ""

    def chave_duplicidade(self) -> str:
        """Chave usada para detectar duplicidade (R6)."""
        v = f"{self.valor_liquido:.2f}" if self.valor_liquido is not None else "?"
        venc = self.vencimento.isoformat() if self.vencimento else "?"
        return f"{self.condominio}|{self.fornecedor}|{self.competencia}|{v}|{venc}".lower()
