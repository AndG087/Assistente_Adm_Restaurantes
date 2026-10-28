from fastapi import FastAPI

from app.api import auth, categorias, contas_pagar, despesas, documentos, fornecedores, health, ia, restaurantes
from app.core.config import get_settings

app = FastAPI(title=get_settings().app_name)

for modulo in (health, auth, restaurantes, fornecedores, categorias, despesas, contas_pagar, documentos, ia):
    app.include_router(modulo.router, prefix="/api")
