from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.api import (
    assistente,
    auth,
    categorias,
    contas_pagar,
    despesas,
    documentos,
    fornecedores,
    health,
    ia,
    membros,
    relatorios,
    restaurantes,
    sugestoes,
)
from app.core.config import get_settings
from app.services.erros import OperacaoNaoPermitidaError, ReferenciaInvalidaError, RegistroDuplicadoError

app = FastAPI(title=get_settings().app_name)

# Erros de regra de negócio dos serviços viram respostas HTTP aqui, num lugar só.
# A mensagem do erro é escrita para o usuário e vai no "detail".
_STATUS_DOS_ERROS = {
    OperacaoNaoPermitidaError: status.HTTP_409_CONFLICT,
    RegistroDuplicadoError: status.HTTP_409_CONFLICT,
    ReferenciaInvalidaError: status.HTTP_422_UNPROCESSABLE_CONTENT,
}


def _responder_erro_de_negocio(_: Request, erro: Exception) -> JSONResponse:
    codigo = next(c for tipo, c in _STATUS_DOS_ERROS.items() if isinstance(erro, tipo))
    return JSONResponse({"detail": str(erro)}, status_code=codigo)


for _tipo in _STATUS_DOS_ERROS:
    app.add_exception_handler(_tipo, _responder_erro_de_negocio)

ROTEADORES = (
    health,
    auth,
    restaurantes,
    membros,
    fornecedores,
    categorias,
    despesas,
    contas_pagar,
    documentos,
    sugestoes,
    assistente,
    relatorios,
    ia,
)
for modulo in ROTEADORES:
    app.include_router(modulo.router, prefix="/api")
