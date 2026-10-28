from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.tempo import agora_utc
from app.models.categoria import CategoriaFinanceira
from app.models.fornecedor import Fornecedor


class Despesa(Base):
    __tablename__ = "despesas"
    # Consulta mais comum: despesas de um restaurante em um período.
    __table_args__ = (
        Index("ix_despesas_restaurante_data", "restaurante_id", "data"),
        UniqueConstraint("conta_pagar_id", name="uq_despesas_conta_pagar_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    restaurante_id: Mapped[int] = mapped_column(ForeignKey("restaurantes.id", ondelete="CASCADE"))
    descricao: Mapped[str] = mapped_column(String(200))
    # DECIMAL exato: dinheiro nunca é guardado como float.
    valor: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    data: Mapped[date] = mapped_column(Date)
    # RESTRICT: categorias e fornecedores em uso não podem ser apagados (eles são inativados).
    categoria_id: Mapped[int | None] = mapped_column(
        ForeignKey("categorias_financeiras.id", ondelete="RESTRICT"), default=None, index=True
    )
    fornecedor_id: Mapped[int | None] = mapped_column(
        ForeignKey("fornecedores.id", ondelete="RESTRICT"), default=None, index=True
    )
    # Número da nota fiscal, boleto ou recibo.
    numero_documento: Mapped[str | None] = mapped_column(String(60), default=None)
    observacoes: Mapped[str | None] = mapped_column(String(500), default=None)
    # Preenchido quando a despesa foi gerada pelo pagamento de uma conta (no máximo uma despesa por conta).
    conta_pagar_id: Mapped[int | None] = mapped_column(
        ForeignKey("contas_pagar.id", ondelete="RESTRICT", name="fk_despesas_conta_pagar_id"), default=None
    )
    criado_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"), default=None)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora_utc)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime, default=agora_utc, onupdate=agora_utc)

    categoria: Mapped[CategoriaFinanceira | None] = relationship(lazy="joined")
    fornecedor: Mapped[Fornecedor | None] = relationship(lazy="joined")
    conta_pagar: Mapped["ContaPagar | None"] = relationship(back_populates="despesa")  # noqa: F821
