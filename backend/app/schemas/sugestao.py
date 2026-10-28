from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.financeiro import Referencia
from app.schemas.validadores import texto_limpo


class PedidoSugestaoCategoria(BaseModel):
    model_config = ConfigDict(extra="forbid")

    descricao: str = Field(min_length=2, max_length=200)
    fornecedor_id: int | None = Field(default=None, gt=0)

    _descricao = field_validator("descricao")(texto_limpo)


class SugestaoCategoriaResponse(BaseModel):
    categoria: Referencia | None
    origem: Literal["palavra_chave", "historico", "ia"] | None
    mensagem: str
