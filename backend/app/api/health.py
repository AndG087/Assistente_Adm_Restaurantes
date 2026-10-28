from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool

from app.core import database
from app.core.config import get_settings
from app.schemas.health import HealthResponse

router = APIRouter(tags=["Saúde"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """O backend está no ar; informa também se o banco de dados responde."""
    banco_ok = await run_in_threadpool(database.verificar_conexao)
    return HealthResponse(
        status="ok",
        banco_de_dados="ok" if banco_ok else "indisponivel",
        modo_demonstracao=get_settings().modo_demonstracao,
    )
