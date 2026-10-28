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
    membros,
    relatorios,
    restaurantes,
    sugestoes,
)
from app.core.config import get_settings

app = FastAPI(title=get_settings().app_name)

ROTEADORES = (
    health,
    auth,
    restaurantes,
    membros,
    fornecedores,
    categorias,
    despesas,
    contas_pagar,
    documentos,
    sugestoes,
    assistente,
    relatorios,
    ia,
)
for modulo in ROTEADORES:
    app.include_router(modulo.router, prefix="/api")
