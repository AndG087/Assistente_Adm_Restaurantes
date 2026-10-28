from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import obter_usuario_atual, obter_usuario_opcional
from app.models import Usuario
from app.schemas.ia import ChatRequest, ChatResponse, IAStatusResponse
from app.services.ollama_service import (
    OllamaError,
    OllamaIndisponivelError,
    OllamaModeloNaoEncontradoError,
    OllamaService,
    OllamaTimeoutError,
    get_ollama_service,
)

router = APIRouter(prefix="/ia", tags=["IA"])


def mensagem_de_erro_do_ollama(erro: OllamaError, modelo: str) -> tuple[int, str]:
    """Status HTTP e mensagem fixa (sem detalhes internos) para cada falha do Ollama."""
    if isinstance(erro, OllamaModeloNaoEncontradoError):
        return status.HTTP_503_SERVICE_UNAVAILABLE, f"O modelo '{modelo}' não está instalado no Ollama."
    if isinstance(erro, OllamaIndisponivelError):
        return (
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "O serviço de IA local (Ollama) não está acessível. Verifique se ele está em execução.",
        )
    if isinstance(erro, OllamaTimeoutError):
        return status.HTTP_504_GATEWAY_TIMEOUT, "A IA demorou demais para responder. Tente novamente."
    return status.HTTP_502_BAD_GATEWAY, "A IA retornou uma resposta inesperada. Tente novamente."


# Público para a tela de entrada mostrar se a IA está ligada; o nome do modelo só vai para quem está logado.
@router.get("/status", response_model=IAStatusResponse)
async def status_ia(
    servico: OllamaService = Depends(get_ollama_service),
    usuario: Usuario | None = Depends(obter_usuario_opcional),
) -> IAStatusResponse:
    resultado = await servico.status()
    return IAStatusResponse(
        ollama_disponivel=resultado.ollama_disponivel,
        modelo=resultado.modelo if usuario else None,
        modelo_disponivel=resultado.modelo_disponivel,
    )


# O chat exige login.
@router.post("/chat", response_model=ChatResponse, dependencies=[Depends(obter_usuario_atual)])
async def chat(
    requisicao: ChatRequest,
    servico: OllamaService = Depends(get_ollama_service),
) -> ChatResponse:
    try:
        resposta = await servico.conversar(requisicao.mensagem)
    except OllamaError as erro:
        codigo, mensagem = mensagem_de_erro_do_ollama(erro, servico.modelo)
        raise HTTPException(codigo, detail=mensagem) from None

    return ChatResponse(resposta=resposta, modelo=servico.modelo)
