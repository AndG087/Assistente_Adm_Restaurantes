"""Detecção de documentos e lançamentos possivelmente duplicados.

São AVISOS para o usuário decidir; nada é bloqueado automaticamente, porque
duas compras iguais no mesmo dia podem ser legítimas.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ContaPagar, Despesa, Documento, StatusDocumento

_JANELA_DIAS = 3
_LIMITE = 10


@dataclass(frozen=True)
class PossivelDuplicado:
    tipo: str  # "despesa", "conta" ou "documento"
    id: int
    descricao: str
    valor: Decimal | None
    data: date | None
    motivo: str


def procurar(
    db: Session,
    restaurante_id: int,
    documento_id: int | None,
    chave_acesso: str | None,
    numero_documento: str | None,
    fornecedor_id: int | None,
    valor: Decimal | None,
    data: date | None,
) -> list[PossivelDuplicado]:
    achados: dict[tuple[str, int], PossivelDuplicado] = {}
    # Despesa -> conta que a gerou (pagamento), para não listar a mesma operação duas vezes.
    conta_de: dict[int, int | None] = {}

    def anotar(item: PossivelDuplicado) -> None:
        achados.setdefault((item.tipo, item.id), item)

    # 1. Outro documento com a mesma chave de acesso da NF-e: é a mesma nota.
    if chave_acesso:
        consulta = select(Documento).where(
            Documento.restaurante_id == restaurante_id,
            Documento.chave_acesso == chave_acesso,
            Documento.status != StatusDocumento.DESCARTADO,
        )
        if documento_id is not None:
            consulta = consulta.where(Documento.id != documento_id)
        for outro in db.scalars(consulta):
            valor_outro = (outro.dados_extraidos or {}).get("valor")
            anotar(
                PossivelDuplicado(
                    tipo="documento",
                    id=outro.id,
                    descricao=outro.nome_original,
                    valor=Decimal(valor_outro) if valor_outro else None,
                    data=outro.criado_em.date(),
                    motivo="Mesma chave de acesso da NF-e",
                )
            )

    for modelo, tipo, coluna_data in (
        (Despesa, "despesa", Despesa.data),
        (ContaPagar, "conta", ContaPagar.data_vencimento),
    ):
        base = select(modelo).where(modelo.restaurante_id == restaurante_id)

        # 2. Mesmo número de documento do mesmo fornecedor.
        if numero_documento and fornecedor_id:
            consulta = base.where(
                modelo.fornecedor_id == fornecedor_id,
                modelo.numero_documento.contains(numero_documento, autoescape=True),
            )
            for item in db.scalars(consulta).unique():
                anotar(_item(item, tipo, "Mesmo número de documento e fornecedor", conta_de))

        # 3. Mesmo valor em data próxima.
        if valor is not None and data is not None:
            consulta = base.where(
                modelo.valor == valor,
                coluna_data.between(data - timedelta(days=_JANELA_DIAS), data + timedelta(days=_JANELA_DIAS)),
            )
            for item in db.scalars(consulta).unique():
                anotar(_item(item, tipo, "Mesmo valor em data próxima", conta_de))

    # A despesa gerada pelo pagamento de uma conta já listada é a mesma operação: mostra só a conta.
    contas = {i.id for i in achados.values() if i.tipo == "conta"}
    resultado = [i for i in achados.values() if not (i.tipo == "despesa" and conta_de.get(i.id) in contas)]
    return resultado[:_LIMITE]


def _item(
    lancamento: Despesa | ContaPagar, tipo: str, motivo: str, conta_de: dict[int, int | None]
) -> PossivelDuplicado:
    if isinstance(lancamento, Despesa):
        conta_de[lancamento.id] = lancamento.conta_pagar_id
        data = lancamento.data
    else:
        data = lancamento.data_vencimento
    return PossivelDuplicado(tipo, lancamento.id, lancamento.descricao, lancamento.valor, data, motivo)
