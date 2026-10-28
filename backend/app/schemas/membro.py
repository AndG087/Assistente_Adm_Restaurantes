from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import PapelMembro
from app.schemas.validadores import normalizar_email


class NovoMembro(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(max_length=254)
    papel: PapelMembro = PapelMembro.MEMBRO

    @field_validator("email")
    @classmethod
    def _email(cls, valor: str) -> str:
        email = normalizar_email(valor)
        if email is None:
            raise ValueError("Informe o e-mail.")
        return email


class AlteracaoPapel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    papel: PapelMembro


class MembroResponse(BaseModel):
    usuario_id: int
    nome: str
    email: str
    papel: PapelMembro
    voce: bool
