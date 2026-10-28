from datetime import date
from typing import Annotated

from fastapi import APIRouter, Body, HTTPException, Path, Query, status

from app.api.deps import DbSession, UsuarioAtual, VinculoRestaurante
from app.core import tempo
from app.models import ContaPagar
from app.schemas.conta_pagar import (
    AlertasVencimento,
    ContaPagarCreate,
    ContaPagarResponse,
    FiltroSituacao,
    GrupoAlerta,
    ListaContasPagar,
    PagamentoRequest,
)
from app.schemas.financeiro import Referencia
from app.services import conta_pagar_service
from app.services.conta_pagar_service import FiltroContas
from app.services.erros import OperacaoNaoPermitidaError, ReferenciaInvalidaError

router = APIRouter(prefix="/restaurantes/{restaurante_id}/contas-a-pagar", tags=["Contas a pagar"])

IdPositivo = Annotated[int, Path(gt=0)]


def _resposta(conta: ContaPagar, hoje: date) -> ContaPagarResponse:
    return ContaPagarResponse(
        id=conta.id,
        descricao=conta.descricao,
        valor=conta.valor,
        data_vencimento=conta.data_vencimento,
        data_pagamento=conta.data_pagamento,
        situacao=conta_pagar_service.situacao(conta, hoje),
        categoria=Referencia.model_validate(conta.categoria) if conta.categoria else None,
        fornecedor=Referencia.model_validate(conta.fornecedor) if conta.fornecedor else None,
        numero_documento=conta.numero_documento,
        observacoes=conta.observacoes,
        despesa_id=conta.despesa.id if conta.despesa else None,
        criado_em=conta.criado_em,
    )


def _obter_ou_404(db: DbSession, vinculo: VinculoRestaurante, conta_id: int) -> ContaPagar:
    conta = conta_pagar_service.obter(db, vinculo.restaurante_id, conta_id)
    if conta is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Conta não encontrada.")
    return conta


def _conflito(erro: Exception) -> HTTPException:
    return HTTPException(status.HTTP_409_CONFLICT, detail=str(erro))


def _invalido(erro: Exception) -> HTTPException:
    return HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(erro))


@router.get("", response_model=ListaContasPagar)
def listar(
    db: DbSession,
    vinculo: VinculoRestaurante,
    situacao: FiltroSituacao = FiltroSituacao.PENDENTES,
    de: date | None = None,
    ate: date | None = None,
    categoria_id: Annotated[int | None, Query(gt=0)] = None,
    fornecedor_id: Annotated[int | None, Query(gt=0)] = None,
    busca: Annotated[str | None, Query(max_length=100)] = None,
    limite: Annotated[int, Query(ge=1, le=200)] = 50,
    deslocamento: Annotated[int, Query(ge=0)] = 0,
) -> ListaContasPagar:
    if de and ate and de > ate:
        raise _invalido(ValueError("A data inicial é posterior à final."))
    filtro = FiltroContas(situacao, de, ate, categoria_id, fornecedor_id, (busca or "").strip() or None)
    contas, total, valor_total = conta_pagar_service.listar(db, vinculo.restaurante_id, filtro, limite, deslocamento)
    hoje = tempo.hoje()
    return ListaContasPagar(itens=[_resposta(c, hoje) for c in contas], total=total, valor_total=valor_total)


# Declarada antes de /{conta_id} para "alertas" não ser lido como um id.
@router.get("/alertas", response_model=AlertasVencimento)
def alertas(
    db: DbSession, vinculo: VinculoRestaurante, dias: Annotated[int, Query(ge=1, le=60)] = 7
) -> AlertasVencimento:
    hoje, grupos = conta_pagar_service.alertas(db, vinculo.restaurante_id, dias)
    return AlertasVencimento(
        hoje=hoje,
        dias=dias,
        **{nome: GrupoAlerta(quantidade=q, valor_total=v) for nome, (q, v) in grupos.items()},
    )


@router.post("", response_model=ContaPagarResponse, status_code=status.HTTP_201_CREATED)
def criar(
    dados: ContaPagarCreate, db: DbSession, vinculo: VinculoRestaurante, usuario: UsuarioAtual
) -> ContaPagarResponse:
    try:
        conta = conta_pagar_service.criar(db, vinculo.restaurante_id, usuario.id, dados)
    except ReferenciaInvalidaError as erro:
        raise _invalido(erro) from None
    return _resposta(conta, tempo.hoje())


@router.get("/{conta_id}", response_model=ContaPagarResponse)
def obter(db: DbSession, vinculo: VinculoRestaurante, conta_id: IdPositivo) -> ContaPagarResponse:
    return _resposta(_obter_ou_404(db, vinculo, conta_id), tempo.hoje())


@router.put("/{conta_id}", response_model=ContaPagarResponse)
def atualizar(
    dados: ContaPagarCreate, db: DbSession, vinculo: VinculoRestaurante, conta_id: IdPositivo
) -> ContaPagarResponse:
    conta = _obter_ou_404(db, vinculo, conta_id)
    try:
        conta = conta_pagar_service.atualizar(db, conta, dados)
    except ReferenciaInvalidaError as erro:
        raise _invalido(erro) from None
    except OperacaoNaoPermitidaError as erro:
        raise _conflito(erro) from None
    return _resposta(conta, tempo.hoje())


@router.delete("/{conta_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir(db: DbSession, vinculo: VinculoRestaurante, conta_id: IdPositivo) -> None:
    conta = _obter_ou_404(db, vinculo, conta_id)
    try:
        conta_pagar_service.excluir(db, conta)
    except OperacaoNaoPermitidaError as erro:
        raise _conflito(erro) from None


@router.post("/{conta_id}/pagar", response_model=ContaPagarResponse)
def pagar(
    db: DbSession,
    vinculo: VinculoRestaurante,
    usuario: UsuarioAtual,
    conta_id: IdPositivo,
    dados: Annotated[PagamentoRequest | None, Body()] = None,
) -> ContaPagarResponse:
    conta = _obter_ou_404(db, vinculo, conta_id)
    try:
        conta = conta_pagar_service.pagar(db, conta, usuario.id, dados.data_pagamento if dados else None)
    except OperacaoNaoPermitidaError as erro:
        raise _conflito(erro) from None
    return _resposta(conta, tempo.hoje())


@router.post("/{conta_id}/desfazer-pagamento", response_model=ContaPagarResponse)
def desfazer_pagamento(db: DbSession, vinculo: VinculoRestaurante, conta_id: IdPositivo) -> ContaPagarResponse:
    conta = _obter_ou_404(db, vinculo, conta_id)
    try:
        conta = conta_pagar_service.desfazer_pagamento(db, conta)
    except OperacaoNaoPermitidaError as erro:
        raise _conflito(erro) from None
    return _resposta(conta, tempo.hoje())
