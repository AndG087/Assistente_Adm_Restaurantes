"""Despesas de um restaurante. Todos os valores somados aqui vêm do banco (SUM em DECIMAL)."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import ColumnElement, Select, func, or_, select
from sqlalchemy.orm import Session

from app.models import CategoriaFinanceira, Despesa
from app.schemas.despesa import DespesaCreate
from app.services import referencias
from app.services.erros import OperacaoNaoPermitidaError


@dataclass(frozen=True)
class FiltroDespesas:
    de: date | None = None
    ate: date | None = None
    categoria_id: int | None = None
    sem_categoria: bool = False
    fornecedor_id: int | None = None
    busca: str | None = None


def _condicoes(restaurante_id: int, filtro: FiltroDespesas) -> list[ColumnElement[bool]]:
    condicoes = [Despesa.restaurante_id == restaurante_id]
    if filtro.de:
        condicoes.append(Despesa.data >= filtro.de)
    if filtro.ate:
        condicoes.append(Despesa.data <= filtro.ate)
    if filtro.sem_categoria:
        condicoes.append(Despesa.categoria_id.is_(None))
    elif filtro.categoria_id:
        condicoes.append(Despesa.categoria_id == filtro.categoria_id)
    if filtro.fornecedor_id:
        condicoes.append(Despesa.fornecedor_id == filtro.fornecedor_id)
    if filtro.busca:
        condicoes.append(
            or_(
                Despesa.descricao.contains(filtro.busca, autoescape=True),
                Despesa.numero_documento.contains(filtro.busca, autoescape=True),
            )
        )
    return condicoes


def listar(
    db: Session, restaurante_id: int, filtro: FiltroDespesas, limite: int, deslocamento: int
) -> tuple[list[Despesa], int, Decimal]:
    condicoes = _condicoes(restaurante_id, filtro)
    total, valor_total = db.execute(
        select(func.count(Despesa.id), func.coalesce(func.sum(Despesa.valor), 0)).where(*condicoes)
    ).one()
    consulta: Select[tuple[Despesa]] = (
        select(Despesa)
        .where(*condicoes)
        .order_by(Despesa.data.desc(), Despesa.id.desc())
        .limit(limite)
        .offset(deslocamento)
    )
    return list(db.scalars(consulta)), total, Decimal(valor_total)


def resumo_por_categoria(
    db: Session, restaurante_id: int, de: date | None, ate: date | None
) -> list[tuple[CategoriaFinanceira | None, int, Decimal]]:
    """Total por categoria no período, do maior para o menor. Sem categoria aparece como None."""
    condicoes = _condicoes(restaurante_id, FiltroDespesas(de=de, ate=ate))
    soma = func.sum(Despesa.valor)
    linhas = db.execute(
        select(Despesa.categoria_id, func.count(Despesa.id), soma)
        .where(*condicoes)
        .group_by(Despesa.categoria_id)
        .order_by(soma.desc())
    ).all()
    ids = [categoria_id for categoria_id, _, _ in linhas if categoria_id is not None]
    categorias = {c.id: c for c in db.scalars(select(CategoriaFinanceira).where(CategoriaFinanceira.id.in_(ids)))}
    return [(categorias.get(cid) if cid else None, quantidade, Decimal(valor)) for cid, quantidade, valor in linhas]


def obter(db: Session, restaurante_id: int, despesa_id: int) -> Despesa | None:
    return db.scalar(select(Despesa).where(Despesa.id == despesa_id, Despesa.restaurante_id == restaurante_id))


def criar(db: Session, restaurante_id: int, usuario_id: int, dados: DespesaCreate) -> Despesa:
    referencias.validar(db, restaurante_id, dados.categoria_id, dados.fornecedor_id)
    despesa = Despesa(restaurante_id=restaurante_id, criado_por_id=usuario_id, **dados.model_dump())
    db.add(despesa)
    db.commit()
    db.refresh(despesa)
    return despesa


def atualizar(db: Session, despesa: Despesa, dados: DespesaCreate) -> Despesa:
    _garantir_editavel(despesa)
    referencias.validar(
        db,
        despesa.restaurante_id,
        dados.categoria_id,
        dados.fornecedor_id,
        categoria_atual=despesa.categoria_id,
        fornecedor_atual=despesa.fornecedor_id,
    )
    for campo, valor in dados.model_dump().items():
        setattr(despesa, campo, valor)
    db.commit()
    db.refresh(despesa)
    return despesa


def excluir(db: Session, despesa: Despesa) -> None:
    _garantir_editavel(despesa)
    db.delete(despesa)
    db.commit()


def _garantir_editavel(despesa: Despesa) -> None:
    # Despesas geradas pelo pagamento de uma conta só mudam pela própria conta.
    if despesa.conta_pagar_id is not None:
        raise OperacaoNaoPermitidaError(
            "Esta despesa foi gerada pelo pagamento de uma conta. Para alterá-la, desfaça o pagamento da conta."
        )
