from typing import Literal

from pydantic import BaseModel


class TabelaResponse(BaseModel):
    colunas: list[str]
    linhas: list[list[str]]


class RespostaAssistente(BaseModel):
    resposta: str
    # dados: veio do banco · conversa: modelo sem acesso aos dados · ajuda: pergunta não entendida
    origem: Literal["dados", "conversa", "ajuda"]
    # O que foi consultado, para o usuário conferir a interpretação (ex.: "Total de despesas · 01/10 a 31/10").
    consulta: str | None = None
    interpretado_por: Literal["regras", "ia"] | None = None
    tabela: TabelaResponse | None = None
