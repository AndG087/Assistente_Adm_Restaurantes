from functools import partial
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool

from app.api.deps import DbSession, VinculoRestaurante
from app.api.ia import mensagem_de_erro_do_ollama
from app.core import tempo
from app.schemas.assistente import RespostaAssistente, TabelaResponse
from app.schemas.ia import ChatRequest
from app.services.assistente import servico
from app.services.ollama_service import OllamaError, OllamaService, get_ollama_service

router = APIRouter(prefix="/restaurantes/{restaurante_id}/assistente", tags=["Assistente"])


@router.post("", response_model=RespostaAssistente)
async def perguntar(
    pergunta: ChatRequest,
    db: DbSession,
    vinculo: VinculoRestaurante,
    ollama: Annotated[OllamaService, Depends(get_ollama_service)],
) -> RespostaAssistente:
    hoje = tempo.hoje()
    # O restaurante vem do vínculo do usuário logado, nunca da pergunta: o assistente não alcança outros dados.
    restaurante_id = vinculo.restaurante_id
    contexto = await run_in_threadpool(servico.carregar_contexto, db, restaurante_id)

    async def executar(plano):
        return await run_in_threadpool(partial(servico.executar_plano, db, restaurante_id, plano, hoje))

    try:
        resposta = await servico.responder(pergunta.mensagem, contexto, hoje, ollama, executar)
    except OllamaError as erro:
        codigo, mensagem = mensagem_de_erro_do_ollama(erro, ollama.modelo)
        raise HTTPException(codigo, detail=mensagem) from None

    resultado = resposta.resultado
    return RespostaAssistente(
        resposta=resposta.texto,
        origem=resposta.origem,
        consulta=resultado.consulta if resultado else None,
        interpretado_por=resposta.interpretado_por,
        tabela=TabelaResponse(colunas=resultado.tabela.colunas, linhas=resultado.tabela.linhas)
        if resultado and resultado.tabela
        else None,
    )
