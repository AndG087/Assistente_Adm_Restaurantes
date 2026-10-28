from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.tempo import agora_utc


class CategoriaFinanceira(Base):
    __tablename__ = "categorias_financeiras"
    # A collation do banco (utf8mb4_unicode_ci) ignora maiúsculas e acentos: "Gás" e "gas" contam como iguais.
    __table_args__ = (UniqueConstraint("restaurante_id", "nome", name="uq_categorias_restaurante_nome"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    restaurante_id: Mapped[int] = mapped_column(ForeignKey("restaurantes.id", ondelete="CASCADE"), index=True)
    nome: Mapped[str] = mapped_column(String(60))
    # Categorias não são apagadas (podem estar em despesas); são inativadas.
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora_utc)
