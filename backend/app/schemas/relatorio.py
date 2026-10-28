from pydantic import BaseModel

from app.schemas.financeiro import DinheiroResposta, Referencia


class TotalMesResponse(BaseModel):
    ano: int
    mes: int
    rotulo: str  # "out/2026"
    quantidade: int
    valor_total: DinheiroResposta


class EvolucaoMensal(BaseModel):
    meses: list[TotalMesResponse]
    # Média dos meses completos (sem o mês atual, que ainda está em andamento).
    media_mensal: DinheiroResposta


class TotalFornecedor(BaseModel):
    fornecedor: Referencia | None
    quantidade: int
    valor_total: DinheiroResposta
