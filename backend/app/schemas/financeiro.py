"""Tipos comuns aos lançamentos financeiros (despesas e contas a pagar)."""

from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer, field_validator

from app.schemas.validadores import opcional, texto_limpo

# Valor em reais: positivo, até 9.999.999.999,99, no máximo 2 casas decimais.
# Sai no JSON como texto ("1234.50") para não perder precisão em clientes que usam float.
Dinheiro = Annotated[
    Decimal,
    Field(gt=0, max_digits=12, decimal_places=2),
    PlainSerializer(lambda v: f"{v:.2f}", return_type=str, when_used="json"),
]
DinheiroResposta = Annotated[Decimal, PlainSerializer(lambda v: f"{v:.2f}", return_type=str, when_used="json")]

# Limites de bom senso para datas digitadas (evita, por exemplo, ano 0202 por engano).
DATA_MINIMA = date(2000, 1, 1)
DATA_MAXIMA = date(2100, 12, 31)
DataLancamento = Annotated[date, Field(ge=DATA_MINIMA, le=DATA_MAXIMA)]


class LancamentoBase(BaseModel):
    """Campos que despesas e contas a pagar têm em comum."""

    model_config = ConfigDict(extra="forbid")

    descricao: str = Field(min_length=2, max_length=200)
    valor: Dinheiro
    categoria_id: int | None = Field(default=None, gt=0)
    fornecedor_id: int | None = Field(default=None, gt=0)
    numero_documento: str | None = Field(default=None, max_length=60)
    observacoes: str | None = Field(default=None, max_length=500)

    @field_validator("descricao")
    @classmethod
    def _descricao(cls, valor: str) -> str:
        valor = texto_limpo(valor)
        if len(valor) < 2:
            raise ValueError("Informe a descrição.")
        return valor

    _opcionais = field_validator("numero_documento", "observacoes")(opcional)


class Referencia(BaseModel):
    """Categoria ou fornecedor resumido, para exibição junto do lançamento."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
