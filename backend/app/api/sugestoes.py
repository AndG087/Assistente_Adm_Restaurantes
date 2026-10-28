from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.concurrency import run_in_threadpool

from app.api.deps import DbSession, VinculoRestaurante
from app.schemas.financeiro import Referencia
from app.schemas.sugestao import PedidoSugestaoCategoria, SugestaoCategoriaResponse
from app.services import sugestao_categoria
from app.services.ollama_service import OllamaService, get_ollama_service

router = APIRouter(prefix="/restaurantes/{restaurante_id}/sugestoes", tags=["Sugestões"])


@router.post("/categoria", response_model=SugestaoCategoriaResponse)
async def sugerir_categoria(
    pedido: PedidoSugestaoCategoria,
    db: DbSession,
    vinculo: VinculoRestaurante,
    ollama: Annotated[OllamaService, Depends(get_ollama_service)],
) -> SugestaoCategoriaResponse:
    # Consulta ao banco em outra thread (é síncrona); a chamada à IA é assíncrona.
    contexto = await run_in_threadpool(
        sugestao_categoria.preparar, db, vinculo.restaurante_id, pedido.fornecedor_id
    )
    sugestao = await sugestao_categoria.sugerir(contexto, pedido.descricao, ollama)
    return SugestaoCategoriaResponse(
        categoria=Referencia.model_validate(sugestao.categoria) if sugestao.categoria else None,
        origem=sugestao.origem,
        mensagem=sugestao.mensagem,
    )
