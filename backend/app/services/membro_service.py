"""Equipe de um restaurante: quem tem acesso e com qual papel."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import MembroRestaurante, PapelMembro, Usuario
from app.services.erros import OperacaoNaoPermitidaError, ReferenciaInvalidaError, RegistroDuplicadoError


def listar(db: Session, restaurante_id: int) -> list[MembroRestaurante]:
    return list(
        db.scalars(
            select(MembroRestaurante)
            .join(MembroRestaurante.usuario)
            .where(MembroRestaurante.restaurante_id == restaurante_id)
            .order_by(MembroRestaurante.papel.desc(), Usuario.nome)
        )
    )


def obter(db: Session, restaurante_id: int, usuario_id: int) -> MembroRestaurante | None:
    return db.scalar(
        select(MembroRestaurante).where(
            MembroRestaurante.restaurante_id == restaurante_id, MembroRestaurante.usuario_id == usuario_id
        )
    )


def _proprietarios(db: Session, restaurante_id: int) -> int:
    return db.scalar(
        select(func.count()).where(
            MembroRestaurante.restaurante_id == restaurante_id,
            MembroRestaurante.papel == PapelMembro.PROPRIETARIO,
        )
    )


def _garantir_outro_proprietario(db: Session, membro: MembroRestaurante) -> None:
    if membro.papel == PapelMembro.PROPRIETARIO and _proprietarios(db, membro.restaurante_id) <= 1:
        raise OperacaoNaoPermitidaError(
            "O restaurante precisa de pelo menos um proprietário. Promova outra pessoa antes."
        )


def adicionar(db: Session, restaurante_id: int, email: str, papel: PapelMembro) -> MembroRestaurante:
    usuario = db.scalar(select(Usuario).where(Usuario.email == email, Usuario.ativo.is_(True)))
    if usuario is None:
        # Sistema local, sem envio de e-mail: a pessoa precisa criar a conta antes.
        raise ReferenciaInvalidaError("Não existe conta com este e-mail. Peça para a pessoa criar a conta primeiro.")
    if obter(db, restaurante_id, usuario.id) is not None:
        raise RegistroDuplicadoError("Esta pessoa já faz parte da equipe.")
    membro = MembroRestaurante(usuario_id=usuario.id, restaurante_id=restaurante_id, papel=papel)
    db.add(membro)
    db.commit()
    db.refresh(membro)
    return membro


def alterar_papel(db: Session, membro: MembroRestaurante, papel: PapelMembro) -> MembroRestaurante:
    if papel != PapelMembro.PROPRIETARIO:
        _garantir_outro_proprietario(db, membro)
    membro.papel = papel
    db.commit()
    db.refresh(membro)
    return membro


def remover(db: Session, membro: MembroRestaurante) -> None:
    _garantir_outro_proprietario(db, membro)
    db.delete(membro)
    db.commit()
