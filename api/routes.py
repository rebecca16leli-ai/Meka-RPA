from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.services import executar_lancamento_json, validar_condominio

router = APIRouter()


class ValidarCondominioRequest(BaseModel):
    condominio: str


class LancamentoRequest(BaseModel):
    arquivo: str
    confirmar: bool = False

@router.get("/")
def root() -> dict:
    return {"message": "Meka RPA API is running."}

@router.post("/validar-condominio")
def validar_condominio_route(request: ValidarCondominioRequest) -> dict:
    resultado = validar_condominio(request.condominio)
    if not resultado.get("ok"):
        raise HTTPException(status_code=400, detail=resultado.get("erro"))
    return resultado


@router.post("/executar-lancamento")
def executar_lancamento_route(request: LancamentoRequest) -> dict:
    resultado = executar_lancamento_json(request.arquivo, confirmar=request.confirmar)
    if not resultado.get("ok"):
        raise HTTPException(status_code=400, detail=resultado.get("erro"))
    return resultado
