from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.financeiro import DataLancamento, DinheiroResposta, LancamentoBase, Referencia


class DespesaCreate(LancamentoBase):
    data: DataLancamento


class DespesaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    descricao: str
    valor: DinheiroResposta
    data: date
    categoria: Referencia | None
    fornecedor: Referencia | None
    numero_documento: str | None
    observacoes: str | None
    # Se preenchido, a despesa veio do pagamento desta conta e só muda por ela.
    conta_pagar_id: int | None
    criado_em: datetime


class ListaDespesas(BaseModel):
    itens: list[DespesaResponse]
    # Totais de TODAS as despesas que atendem aos filtros, não só da página atual.
    total: int
    valor_total: DinheiroResposta


class TotalCategoria(BaseModel):
    categoria: Referencia | None
    quantidade: int
    valor_total: DinheiroResposta


class ResumoDespesas(BaseModel):
    quantidade: int
    valor_total: DinheiroResposta
    por_categoria: list[TotalCategoria]
