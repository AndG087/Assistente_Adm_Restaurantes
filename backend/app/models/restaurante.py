import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.tempo import agora_utc


class Restaurante(Base):
    __tablename__ = "restaurantes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(120))
    # Somente os 14 dígitos, sem pontuação.
    cnpj: Mapped[str | None] = mapped_column(String(14), default=None)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora_utc)

    membros: Mapped[list["MembroRestaurante"]] = relationship(back_populates="restaurante")


class PapelMembro(enum.StrEnum):
    PROPRIETARIO = "proprietario"
    MEMBRO = "membro"


class MembroRestaurante(Base):
    """Liga um usuário a um restaurante. É a base do isolamento: sem vínculo, sem acesso."""

    __tablename__ = "membros_restaurante"

    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True)
    restaurante_id: Mapped[int] = mapped_column(
        ForeignKey("restaurantes.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    papel: Mapped[PapelMembro] = mapped_column(
        Enum(PapelMembro, values_callable=lambda e: [m.value for m in e], native_enum=False, length=20)
    )
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora_utc)

    usuario: Mapped["Usuario"] = relationship(back_populates="vinculos")  # noqa: F821
    restaurante: Mapped[Restaurante] = relationship(back_populates="membros")
