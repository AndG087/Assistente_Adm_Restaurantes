"""Restaurantes e o vínculo de cada usuário com eles."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import MembroRestaurante, PapelMembro, Restaurante, Usuario


def listar_do_usuario(db: Session, usuario: Usuario) -> list[MembroRestaurante]:
    return list(
        db.scalars(
            select(MembroRestaurante)
            .join(MembroRestaurante.restaurante)
            .where(MembroRestaurante.usuario_id == usuario.id)
            .order_by(Restaurante.nome, Restaurante.id)
        )
    )


def criar(db: Session, usuario: Usuario, nome: str, cnpj: str | None) -> MembroRestaurante:
    """Cria o restaurante e torna o usuário seu proprietário, na mesma transação."""
    restaurante = Restaurante(nome=nome, cnpj=cnpj)
    vinculo = MembroRestaurante(usuario=usuario, restaurante=restaurante, papel=PapelMembro.PROPRIETARIO)
    db.add_all([restaurante, vinculo])
    db.commit()
    return vinculo


def obter_vinculo(db: Session, usuario: Usuario, restaurante_id: int) -> MembroRestaurante | None:
    """Ponto central do isolamento: só devolve algo se o usuário for membro do restaurante."""
    return db.scalar(
        select(MembroRestaurante).where(
            MembroRestaurante.usuario_id == usuario.id,
            MembroRestaurante.restaurante_id == restaurante_id,
        )
    )
