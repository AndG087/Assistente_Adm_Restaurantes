from pydantic import BaseModel, ConfigDict, Field

TAMANHO_MAXIMO_MENSAGEM = 4000


class ChatRequest(BaseModel):
    # str_strip_whitespace faz uma mensagem só com espaços virar "" e falhar em min_length.
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    mensagem: str = Field(min_length=1, max_length=TAMANHO_MAXIMO_MENSAGEM)


class ChatResponse(BaseModel):
    resposta: str
    modelo: str


class IAStatusResponse(BaseModel):
    ollama_disponivel: bool
    modelo: str | None  # None quando ninguém está logado
    modelo_disponivel: bool
