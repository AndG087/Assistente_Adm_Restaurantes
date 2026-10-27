from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import obter_usuario_atual
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


@router.get("/status", response_model=IAStatusResponse)
async def status_ia(servico: OllamaService = Depends(get_ollama_service)) -> IAStatusResponse:
    resultado = await servico.status()
    return IAStatusResponse(
        ollama_disponivel=resultado.ollama_disponivel,
        modelo=resultado.modelo,
        modelo_disponivel=resultado.modelo_disponivel,
    )


# O chat exige login; o status continua público para a tela de entrada poder exibi-lo.
@router.post("/chat", response_model=ChatResponse, dependencies=[Depends(obter_usuario_atual)])
async def chat(
    requisicao: ChatRequest,
    servico: OllamaService = Depends(get_ollama_service),
) -> ChatResponse:
    # As mensagens de erro são fixas para não expor detalhes internos ao cliente.
    try:
        resposta = await servico.conversar(requisicao.mensagem)
    except OllamaModeloNaoEncontradoError:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"O modelo '{servico.modelo}' não está instalado no Ollama.",
        ) from None
    except OllamaIndisponivelError:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="O serviço de IA local (Ollama) não está acessível. Verifique se ele está em execução.",
        ) from None
    except OllamaTimeoutError:
        raise HTTPException(
            status.HTTP_504_GATEWAY_TIMEOUT,
            detail="A IA demorou demais para responder. Tente novamente.",
        ) from None
    except OllamaError:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail="A IA retornou uma resposta inesperada. Tente novamente.",
        ) from None

    return ChatResponse(resposta=resposta, modelo=servico.modelo)
