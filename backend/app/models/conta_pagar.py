from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.tempo import agora_utc
from app.models.categoria import CategoriaFinanceira
from app.models.fornecedor import Fornecedor


class ContaPagar(Base):
    """Conta com vencimento (boleto, fatura, aluguel...). Ao ser paga, gera uma Despesa."""

    __tablename__ = "contas_pagar"
    __table_args__ = (Index("ix_contas_pagar_restaurante_vencimento", "restaurante_id", "data_vencimento"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    restaurante_id: Mapped[int] = mapped_column(ForeignKey("restaurantes.id", ondelete="CASCADE"))
    descricao: Mapped[str] = mapped_column(String(200))
    valor: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    data_vencimento: Mapped[date] = mapped_column(Date)
    # Preenchida quando a conta é paga; a situação (vencida, a vencer...) é calculada a partir das datas.
    data_pagamento: Mapped[date | None] = mapped_column(Date, default=None)
    categoria_id: Mapped[int | None] = mapped_column(
        ForeignKey("categorias_financeiras.id", ondelete="RESTRICT"), default=None, index=True
    )
    fornecedor_id: Mapped[int | None] = mapped_column(
        ForeignKey("fornecedores.id", ondelete="RESTRICT"), default=None, index=True
    )
    numero_documento: Mapped[str | None] = mapped_column(String(60), default=None)
    observacoes: Mapped[str | None] = mapped_column(String(500), default=None)
    criado_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"), default=None)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora_utc)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime, default=agora_utc, onupdate=agora_utc)

    categoria: Mapped[CategoriaFinanceira | None] = relationship(lazy="joined")
    fornecedor: Mapped[Fornecedor | None] = relationship(lazy="joined")
    despesa: Mapped["Despesa | None"] = relationship(back_populates="conta_pagar", lazy="joined")  # noqa: F821
