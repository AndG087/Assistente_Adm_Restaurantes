from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["ok"]
    banco_de_dados: Literal["ok", "indisponivel"]
