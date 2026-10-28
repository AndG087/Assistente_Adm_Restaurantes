from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.tempo import agora_utc


class Fornecedor(Base):
    __tablename__ = "fornecedores"
    # O mesmo CPF/CNPJ não se repete dentro de um restaurante (vários NULL são permitidos).
    __table_args__ = (UniqueConstraint("restaurante_id", "documento", name="uq_fornecedores_restaurante_documento"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    restaurante_id: Mapped[int] = mapped_column(ForeignKey("restaurantes.id", ondelete="CASCADE"), index=True)
    nome: Mapped[str] = mapped_column(String(150))
    # CPF (11) ou CNPJ (14), só dígitos.
    documento: Mapped[str | None] = mapped_column(String(14), default=None)
    telefone: Mapped[str | None] = mapped_column(String(20), default=None)
    email: Mapped[str | None] = mapped_column(String(254), default=None)
    observacoes: Mapped[str | None] = mapped_column(String(500), default=None)
    # Fornecedores não são apagados (podem estar em despesas); são inativados.
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora_utc)
