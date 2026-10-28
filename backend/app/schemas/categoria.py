from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.validadores import texto_limpo


class CategoriaCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome: str = Field(min_length=2, max_length=60)

    @field_validator("nome")
    @classmethod
    def _nome(cls, valor: str) -> str:
        valor = texto_limpo(valor)
        if len(valor) < 2:
            raise ValueError("Informe o nome da categoria.")
        return valor


class CategoriaUpdate(CategoriaCreate):
    ativo: bool = True


class CategoriaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    ativo: bool
