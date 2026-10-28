from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.validadores import (
    normalizar_documento,
    normalizar_email,
    normalizar_telefone,
    opcional,
    texto_limpo,
)


class FornecedorCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome: str = Field(min_length=2, max_length=150)
    documento: str | None = Field(default=None, max_length=18)
    telefone: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=254)
    observacoes: str | None = Field(default=None, max_length=500)

    @field_validator("nome")
    @classmethod
    def _nome(cls, valor: str) -> str:
        valor = texto_limpo(valor)
        if len(valor) < 2:
            raise ValueError("Informe o nome do fornecedor.")
        return valor

    _documento = field_validator("documento")(normalizar_documento)
    _telefone = field_validator("telefone")(normalizar_telefone)
    _email = field_validator("email")(normalizar_email)
    _observacoes = field_validator("observacoes")(opcional)


class FornecedorUpdate(FornecedorCreate):
    """Substitui todos os dados do fornecedor (PUT)."""

    ativo: bool = True


class FornecedorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    documento: str | None
    telefone: str | None
    email: str | None
    observacoes: str | None
    ativo: bool
