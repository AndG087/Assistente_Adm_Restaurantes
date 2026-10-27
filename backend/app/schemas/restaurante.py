from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.restaurante import PapelMembro


def cnpj_valido(digitos: str) -> bool:
    """Confere os dois dígitos verificadores do CNPJ."""
    if len(digitos) != 14 or not digitos.isdigit() or len(set(digitos)) == 1:
        return False

    def digito(base: str) -> str:
        pesos = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2][-len(base) :]
        resto = sum(int(d) * p for d, p in zip(base, pesos, strict=True)) % 11
        return "0" if resto < 2 else str(11 - resto)

    primeiro = digito(digitos[:12])
    segundo = digito(digitos[:12] + primeiro)
    return digitos[12:] == primeiro + segundo


class RestauranteCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome: str = Field(min_length=2, max_length=120)
    cnpj: str | None = Field(default=None, max_length=18)

    @field_validator("nome")
    @classmethod
    def _nome(cls, valor: str) -> str:
        valor = " ".join(valor.split())
        if len(valor) < 2:
            raise ValueError("Informe o nome do restaurante.")
        return valor

    @field_validator("cnpj")
    @classmethod
    def _cnpj(cls, valor: str | None) -> str | None:
        if valor is None or not valor.strip():
            return None
        digitos = "".join(c for c in valor if c.isdigit())
        if not cnpj_valido(digitos):
            raise ValueError("CNPJ inválido.")
        return digitos


class RestauranteResponse(BaseModel):
    id: int
    nome: str
    cnpj: str | None
    papel: PapelMembro
