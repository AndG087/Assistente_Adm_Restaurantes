"""Fornecedores de um restaurante. Toda consulta é filtrada por restaurante_id."""

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Fornecedor
from app.schemas.fornecedor import FornecedorCreate, FornecedorUpdate
from app.schemas.validadores import somente_digitos
from app.services.erros import RegistroDuplicadoError

MENSAGEM_DUPLICADO = "Já existe um fornecedor com este CPF/CNPJ neste restaurante."


def listar(db: Session, restaurante_id: int, busca: str | None, incluir_inativos: bool) -> list[Fornecedor]:
    consulta = select(Fornecedor).where(Fornecedor.restaurante_id == restaurante_id)
    if not incluir_inativos:
        consulta = consulta.where(Fornecedor.ativo.is_(True))
    if busca:
        termos = [Fornecedor.nome.contains(busca, autoescape=True)]
        digitos = somente_digitos(busca)
        if digitos:
            termos.append(Fornecedor.documento.contains(digitos))
        consulta = consulta.where(or_(*termos))
    return list(db.scalars(consulta.order_by(Fornecedor.nome, Fornecedor.id)))


def obter(db: Session, restaurante_id: int, fornecedor_id: int) -> Fornecedor | None:
    return db.scalar(
        select(Fornecedor).where(Fornecedor.id == fornecedor_id, Fornecedor.restaurante_id == restaurante_id)
    )


def _salvar(db: Session, fornecedor: Fornecedor) -> Fornecedor:
    db.add(fornecedor)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise RegistroDuplicadoError(MENSAGEM_DUPLICADO) from None
    return fornecedor


def criar(db: Session, restaurante_id: int, dados: FornecedorCreate) -> Fornecedor:
    return _salvar(db, Fornecedor(restaurante_id=restaurante_id, **dados.model_dump()))


def atualizar(db: Session, fornecedor: Fornecedor, dados: FornecedorUpdate) -> Fornecedor:
    for campo, valor in dados.model_dump().items():
        setattr(fornecedor, campo, valor)
    return _salvar(db, fornecedor)
