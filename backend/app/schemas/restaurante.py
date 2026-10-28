from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.restaurante import PapelMembro
from app.schemas.validadores import normalizar_cnpj, texto_limpo


class RestauranteCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome: str = Field(min_length=2, max_length=120)
    cnpj: str | None = Field(default=None, max_length=18)

    @field_validator("nome")
    @classmethod
    def _nome(cls, valor: str) -> str:
        valor = texto_limpo(valor)
        if len(valor) < 2:
            raise ValueError("Informe o nome do restaurante.")
        return valor

    _cnpj = field_validator("cnpj")(normalizar_cnpj)


class RestauranteResponse(BaseModel):
    id: int
    nome: str
    cnpj: str | None
    papel: PapelMembro
