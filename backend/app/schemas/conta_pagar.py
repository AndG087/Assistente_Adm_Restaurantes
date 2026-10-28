from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from app.schemas.financeiro import DataLancamento, DinheiroResposta, LancamentoBase, Referencia


class Situacao(StrEnum):
    PAGA = "paga"
    VENCIDA = "vencida"
    VENCE_HOJE = "vence_hoje"
    A_VENCER = "a_vencer"


class FiltroSituacao(StrEnum):
    PENDENTES = "pendentes"
    VENCIDAS = "vencidas"
    PAGAS = "pagas"
    TODAS = "todas"


class ContaPagarCreate(LancamentoBase):
    data_vencimento: DataLancamento


class PagamentoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Se omitida, considera hoje.
    data_pagamento: DataLancamento | None = None


class ContaPagarResponse(BaseModel):
    id: int
    descricao: str
    valor: DinheiroResposta
    data_vencimento: date
    data_pagamento: date | None
    situacao: Situacao
    categoria: Referencia | None
    fornecedor: Referencia | None
    numero_documento: str | None
    observacoes: str | None
    # Despesa gerada pelo pagamento, se a conta estiver paga.
    despesa_id: int | None
    criado_em: datetime


class ListaContasPagar(BaseModel):
    itens: list[ContaPagarResponse]
    total: int
    valor_total: DinheiroResposta


class GrupoAlerta(BaseModel):
    quantidade: int
    valor_total: DinheiroResposta


class AlertasVencimento(BaseModel):
    hoje: date
    dias: int
    vencidas: GrupoAlerta
    vencem_hoje: GrupoAlerta
    # Vencem de amanhã até hoje + dias.
    proximos_dias: GrupoAlerta
