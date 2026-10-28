from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query, status

from app.api.deps import DbSession, UsuarioAtual, VinculoRestaurante, ou_404
from app.models import Despesa
from app.schemas.despesa import DespesaCreate, DespesaResponse, ListaDespesas, ResumoDespesas, TotalCategoria
from app.schemas.financeiro import Referencia
from app.services import despesa_service
from app.services.despesa_service import FiltroDespesas

router = APIRouter(prefix="/restaurantes/{restaurante_id}/despesas", tags=["Despesas"])

IdPositivo = Annotated[int, Path(gt=0)]


def _validar_periodo(de: date | None, ate: date | None) -> None:
    if de and ate and de > ate:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail="A data inicial é posterior à final.")


def _obter_ou_404(db: DbSession, vinculo: VinculoRestaurante, despesa_id: int) -> Despesa:
    return ou_404(despesa_service.obter(db, vinculo.restaurante_id, despesa_id), "Despesa não encontrada.")


@router.get("", response_model=ListaDespesas)
def listar(
    db: DbSession,
    vinculo: VinculoRestaurante,
    de: date | None = None,
    ate: date | None = None,
    categoria_id: Annotated[int | None, Query(gt=0)] = None,
    sem_categoria: bool = False,
    fornecedor_id: Annotated[int | None, Query(gt=0)] = None,
    busca: Annotated[str | None, Query(max_length=100)] = None,
    limite: Annotated[int, Query(ge=1, le=200)] = 50,
    deslocamento: Annotated[int, Query(ge=0)] = 0,
) -> ListaDespesas:
    _validar_periodo(de, ate)
    filtro = FiltroDespesas(de, ate, categoria_id, sem_categoria, fornecedor_id, (busca or "").strip() or None)
    itens, total, valor_total = despesa_service.listar(db, vinculo.restaurante_id, filtro, limite, deslocamento)
    return ListaDespesas(
        itens=[DespesaResponse.model_validate(d) for d in itens], total=total, valor_total=valor_total
    )


@router.get("/resumo", response_model=ResumoDespesas)
def resumo(
    db: DbSession, vinculo: VinculoRestaurante, de: date | None = None, ate: date | None = None
) -> ResumoDespesas:
    _validar_periodo(de, ate)
    linhas = despesa_service.resumo_por_categoria(db, vinculo.restaurante_id, de, ate)
    por_categoria = [
        TotalCategoria(
            categoria=Referencia.model_validate(c) if c else None, quantidade=quantidade, valor_total=valor
        )
        for c, quantidade, valor in linhas
    ]
    return ResumoDespesas(
        quantidade=sum(t.quantidade for t in por_categoria),
        valor_total=sum((t.valor_total for t in por_categoria), start=0),
        por_categoria=por_categoria,
    )


@router.post("", response_model=DespesaResponse, status_code=status.HTTP_201_CREATED)
def criar(dados: DespesaCreate, db: DbSession, vinculo: VinculoRestaurante, usuario: UsuarioAtual) -> Despesa:
    return despesa_service.criar(db, vinculo.restaurante_id, usuario.id, dados)


@router.get("/{despesa_id}", response_model=DespesaResponse)
def obter(db: DbSession, vinculo: VinculoRestaurante, despesa_id: IdPositivo) -> Despesa:
    return _obter_ou_404(db, vinculo, despesa_id)


@router.put("/{despesa_id}", response_model=DespesaResponse)
def atualizar(dados: DespesaCreate, db: DbSession, vinculo: VinculoRestaurante, despesa_id: IdPositivo) -> Despesa:
    despesa = _obter_ou_404(db, vinculo, despesa_id)
    return despesa_service.atualizar(db, despesa, dados)


@router.delete("/{despesa_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir(db: DbSession, vinculo: VinculoRestaurante, despesa_id: IdPositivo) -> None:
    despesa = _obter_ou_404(db, vinculo, despesa_id)
    despesa_service.excluir(db, despesa)
