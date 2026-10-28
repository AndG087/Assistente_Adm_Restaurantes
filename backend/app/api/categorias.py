from typing import Annotated

from fastapi import APIRouter, Path, status

from app.api.deps import DbSession, VinculoRestaurante, ou_404
from app.models import CategoriaFinanceira
from app.schemas.categoria import CategoriaCreate, CategoriaResponse, CategoriaUpdate
from app.services import categoria_service

router = APIRouter(prefix="/restaurantes/{restaurante_id}/categorias", tags=["Categorias financeiras"])


@router.get("", response_model=list[CategoriaResponse])
def listar(db: DbSession, vinculo: VinculoRestaurante, incluir_inativas: bool = False) -> list[CategoriaFinanceira]:
    return categoria_service.listar(db, vinculo.restaurante_id, incluir_inativas)


@router.post("", response_model=CategoriaResponse, status_code=status.HTTP_201_CREATED)
def criar(dados: CategoriaCreate, db: DbSession, vinculo: VinculoRestaurante) -> CategoriaFinanceira:
    return categoria_service.criar(db, vinculo.restaurante_id, dados.nome)


@router.put("/{categoria_id}", response_model=CategoriaResponse)
def atualizar(
    dados: CategoriaUpdate,
    db: DbSession,
    vinculo: VinculoRestaurante,
    categoria_id: Annotated[int, Path(gt=0)],
) -> CategoriaFinanceira:
    categoria = ou_404(categoria_service.obter(db, vinculo.restaurante_id, categoria_id), "Categoria não encontrada.")
    return categoria_service.atualizar(db, categoria, dados.nome, dados.ativo)
