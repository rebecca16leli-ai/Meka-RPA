from __future__ import annotations
from fastapi import FastAPI
from api.routes import router

app = FastAPI(title="Meka RPA API")

app.include_router(router)
