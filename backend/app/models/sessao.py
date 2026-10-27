from datetime import datetime

from sqlalchemy import CHAR, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.tempo import agora_utc


class Sessao(Base):
    """Sessão de login. Guarda apenas o hash SHA-256 do token enviado no cookie."""

    __tablename__ = "sessoes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(CHAR(64), unique=True)
    criada_em: Mapped[datetime] = mapped_column(DateTime, default=agora_utc)
    expira_em: Mapped[datetime] = mapped_column(DateTime)

    usuario: Mapped["Usuario"] = relationship()  # noqa: F821
