import enum
from datetime import datetime
from typing import Any

from sqlalchemy import CHAR, JSON, DateTime, Enum, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.tempo import agora_utc
from app.models.conta_pagar import ContaPagar
from app.models.despesa import Despesa


class StatusDocumento(enum.StrEnum):
    # Texto extraído; aguarda o usuário conferir e gerar o lançamento.
    PENDENTE = "pendente"
    # Conferido: virou uma despesa ou conta a pagar.
    CONCLUIDO = "concluido"
    DESCARTADO = "descartado"
    # Não foi possível extrair o texto (arquivo ilegível, OCR indisponível...).
    ERRO = "erro"


class Documento(Base):
    """Nota fiscal, boleto ou comprovante enviado. O arquivo fica no disco local; aqui ficam os metadados."""

    __tablename__ = "documentos"
    __table_args__ = (
        # O mesmo arquivo (mesmo conteúdo) não entra duas vezes no mesmo restaurante.
        UniqueConstraint("restaurante_id", "sha256", name="uq_documentos_restaurante_sha256"),
        Index("ix_documentos_restaurante_criado", "restaurante_id", "criado_em"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    restaurante_id: Mapped[int] = mapped_column(ForeignKey("restaurantes.id", ondelete="CASCADE"))
    # Nome que o usuário deu ao arquivo; só para exibição, nunca usado como caminho.
    nome_original: Mapped[str] = mapped_column(String(255))
    tipo_mime: Mapped[str] = mapped_column(String(50))
    tamanho_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(CHAR(64))
    # Caminho relativo à pasta de documentos, gerado pelo sistema (ex.: "3/4f1c...e2.pdf").
    arquivo: Mapped[str] = mapped_column(String(120))
    status: Mapped[StatusDocumento] = mapped_column(
        Enum(StatusDocumento, values_callable=lambda e: [m.value for m in e], native_enum=False, length=20)
    )
    # "pdf_texto" (texto embutido no PDF) ou "ocr".
    metodo_extracao: Mapped[str | None] = mapped_column(String(20), default=None)
    texto_extraido: Mapped[str | None] = mapped_column(Text().with_variant(MEDIUMTEXT(), "mysql"), default=None)
    erro: Mapped[str | None] = mapped_column(String(300), default=None)
    # Campos encontrados no texto por regras fixas (valor, datas, CNPJ...). São sugestões, não verdades.
    dados_extraidos: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    # Chave de acesso da NF-e (44 dígitos), usada para detectar notas repetidas.
    chave_acesso: Mapped[str | None] = mapped_column(CHAR(44), default=None, index=True)
    # Lançamento gerado na conferência.
    despesa_id: Mapped[int | None] = mapped_column(ForeignKey("despesas.id", ondelete="SET NULL"), default=None)
    conta_pagar_id: Mapped[int | None] = mapped_column(
        ForeignKey("contas_pagar.id", ondelete="SET NULL"), default=None
    )
    enviado_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"), default=None)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora_utc)
    processado_em: Mapped[datetime | None] = mapped_column(DateTime, default=None)

    despesa: Mapped[Despesa | None] = relationship()
    conta_pagar: Mapped[ContaPagar | None] = relationship()
