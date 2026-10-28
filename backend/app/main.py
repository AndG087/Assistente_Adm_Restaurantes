from fastapi import FastAPI

from app.api import (
    assistente,
    auth,
    categorias,
    contas_pagar,
    despesas,
    documentos,
    fornecedores,
    health,
    ia,
    restaurantes,
    sugestoes,
)
from app.core.config import get_settings

app = FastAPI(title=get_settings().app_name)

ROTEADORES = (
    health,
    auth,
    restaurantes,
    fornecedores,
    categorias,
    despesas,
    contas_pagar,
    documentos,
    sugestoes,
    assistente,
    ia,
)
for modulo in ROTEADORES:
    app.include_router(modulo.router, prefix="/api")
