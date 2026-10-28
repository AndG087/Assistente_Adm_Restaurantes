"""Categorias financeiras de um restaurante. Toda consulta é filtrada por restaurante_id."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import CategoriaFinanceira
from app.services.erros import RegistroDuplicadoError

# Criadas junto com cada restaurante novo; o usuário pode renomear, inativar ou criar outras.
CATEGORIAS_PADRAO = [
    "Alimentos e insumos",
    "Bebidas",
    "Embalagens e descartáveis",
    "Limpeza e higiene",
    "Aluguel",
    "Energia elétrica",
    "Água e esgoto",
    "Gás",
    "Folha de pagamento",
    "Impostos e taxas",
    "Manutenção",
    "Marketing",
    "Serviços e assinaturas",
    "Outros",
]

MENSAGEM_DUPLICADA = "Já existe uma categoria com este nome neste restaurante."


def categorias_padrao(restaurante_id: int | None = None) -> list[CategoriaFinanceira]:
    return [CategoriaFinanceira(restaurante_id=restaurante_id, nome=nome) for nome in CATEGORIAS_PADRAO]


def listar(db: Session, restaurante_id: int, incluir_inativas: bool) -> list[CategoriaFinanceira]:
    consulta = select(CategoriaFinanceira).where(CategoriaFinanceira.restaurante_id == restaurante_id)
    if not incluir_inativas:
        consulta = consulta.where(CategoriaFinanceira.ativo.is_(True))
    return list(db.scalars(consulta.order_by(CategoriaFinanceira.nome, CategoriaFinanceira.id)))


def obter(db: Session, restaurante_id: int, categoria_id: int) -> CategoriaFinanceira | None:
    return db.scalar(
        select(CategoriaFinanceira).where(
            CategoriaFinanceira.id == categoria_id, CategoriaFinanceira.restaurante_id == restaurante_id
        )
    )


def _salvar(db: Session, categoria: CategoriaFinanceira) -> CategoriaFinanceira:
    db.add(categoria)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise RegistroDuplicadoError(MENSAGEM_DUPLICADA) from None
    return categoria


def criar(db: Session, restaurante_id: int, nome: str) -> CategoriaFinanceira:
    return _salvar(db, CategoriaFinanceira(restaurante_id=restaurante_id, nome=nome))


def atualizar(db: Session, categoria: CategoriaFinanceira, nome: str, ativo: bool) -> CategoriaFinanceira:
    categoria.nome = nome
    categoria.ativo = ativo
    return _salvar(db, categoria)
