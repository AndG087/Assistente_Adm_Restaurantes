import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Validação simples e suficiente: algo@dominio.ext, sem espaços.
_PADRAO_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _normalizar_email(valor: str) -> str:
    valor = valor.strip().lower()
    if not _PADRAO_EMAIL.match(valor):
        raise ValueError("E-mail inválido.")
    return valor


class RegistroRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome: str = Field(min_length=2, max_length=120)
    email: str = Field(max_length=254)
    senha: str = Field(min_length=8, max_length=128)

    @field_validator("nome")
    @classmethod
    def _nome(cls, valor: str) -> str:
        valor = " ".join(valor.split())
        if len(valor) < 2:
            raise ValueError("Informe o nome.")
        return valor

    _email = field_validator("email")(_normalizar_email)


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(max_length=254)
    senha: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def _email(cls, valor: str) -> str:
        # No login não validamos o formato: um e-mail malformado simplesmente não será encontrado.
        return valor.strip().lower()


class UsuarioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    email: str
