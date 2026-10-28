from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query, status

from app.api.deps import DbSession, VinculoRestaurante
from app.models import Fornecedor
from app.schemas.fornecedor import FornecedorCreate, FornecedorResponse, FornecedorUpdate
from app.services import fornecedor_service
from app.services.erros import RegistroDuplicadoError

router = APIRouter(prefix="/restaurantes/{restaurante_id}/fornecedores", tags=["Fornecedores"])


def _obter_ou_404(db: DbSession, vinculo: VinculoRestaurante, fornecedor_id: int) -> Fornecedor:
    fornecedor = fornecedor_service.obter(db, vinculo.restaurante_id, fornecedor_id)
    if fornecedor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Fornecedor não encontrado.")
    return fornecedor


@router.get("", response_model=list[FornecedorResponse])
def listar(
    db: DbSession,
    vinculo: VinculoRestaurante,
    busca: Annotated[str | None, Query(max_length=100)] = None,
    incluir_inativos: bool = False,
) -> list[Fornecedor]:
    return fornecedor_service.listar(db, vinculo.restaurante_id, (busca or "").strip() or None, incluir_inativos)


@router.post("", response_model=FornecedorResponse, status_code=status.HTTP_201_CREATED)
def criar(dados: FornecedorCreate, db: DbSession, vinculo: VinculoRestaurante) -> Fornecedor:
    try:
        return fornecedor_service.criar(db, vinculo.restaurante_id, dados)
    except RegistroDuplicadoError as erro:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(erro)) from None


@router.get("/{fornecedor_id}", response_model=FornecedorResponse)
def obter(db: DbSession, vinculo: VinculoRestaurante, fornecedor_id: Annotated[int, Path(gt=0)]) -> Fornecedor:
    return _obter_ou_404(db, vinculo, fornecedor_id)


@router.put("/{fornecedor_id}", response_model=FornecedorResponse)
def atualizar(
    dados: FornecedorUpdate,
    db: DbSession,
    vinculo: VinculoRestaurante,
    fornecedor_id: Annotated[int, Path(gt=0)],
) -> Fornecedor:
    fornecedor = _obter_ou_404(db, vinculo, fornecedor_id)
    try:
        return fornecedor_service.atualizar(db, fornecedor, dados)
    except RegistroDuplicadoError as erro:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(erro)) from None
