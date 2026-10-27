from fastapi import FastAPI

from app.api import auth, health, ia, restaurantes
from app.core.config import get_settings

app = FastAPI(title=get_settings().app_name)

app.include_router(health.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(restaurantes.router, prefix="/api")
app.include_router(ia.router, prefix="/api")
