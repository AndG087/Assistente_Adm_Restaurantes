from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.api.deps import DbSession, VinculoRestaurante
from app.schemas.financeiro import Referencia
from app.schemas.validadores import texto_limpo
from app.services import sugestao_categoria
from app.services.ollama_service import OllamaService, get_ollama_service

router = APIRouter(prefix="/restaurantes/{restaurante_id}/sugestoes", tags=["Sugestões"])


class PedidoSugestaoCategoria(BaseModel):
    model_config = ConfigDict(extra="forbid")

    descricao: str = Field(min_length=2, max_length=200)
    fornecedor_id: int | None = Field(default=None, gt=0)

    _descricao = field_validator("descricao")(texto_limpo)


class SugestaoCategoriaResponse(BaseModel):
    categoria: Referencia | None
    origem: Literal["palavra_chave", "historico", "ia"] | None
    mensagem: str


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
