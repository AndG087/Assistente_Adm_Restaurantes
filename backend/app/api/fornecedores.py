from typing import Annotated

from fastapi import APIRouter, Path, Query, status

from app.api.deps import DbSession, VinculoRestaurante, ou_404
from app.models import Fornecedor
from app.schemas.fornecedor import FornecedorCreate, FornecedorResponse, FornecedorUpdate
from app.services import fornecedor_service

router = APIRouter(prefix="/restaurantes/{restaurante_id}/fornecedores", tags=["Fornecedores"])


def _obter_ou_404(db: DbSession, vinculo: VinculoRestaurante, fornecedor_id: int) -> Fornecedor:
    return ou_404(fornecedor_service.obter(db, vinculo.restaurante_id, fornecedor_id), "Fornecedor não encontrado.")


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
    return fornecedor_service.criar(db, vinculo.restaurante_id, dados)


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
    return fornecedor_service.atualizar(db, fornecedor, dados)
