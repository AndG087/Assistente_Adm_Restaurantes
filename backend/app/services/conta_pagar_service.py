"""Contas a pagar: vencimentos, pagamento (que gera a despesa) e alertas."""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.orm import Session

from app.core import tempo
from app.models import ContaPagar, Despesa
from app.schemas.conta_pagar import ContaPagarCreate, FiltroSituacao, Situacao
from app.services import referencias
from app.services.erros import OperacaoNaoPermitidaError


def situacao(conta: ContaPagar, hoje: date) -> Situacao:
    if conta.data_pagamento is not None:
        return Situacao.PAGA
    if conta.data_vencimento < hoje:
        return Situacao.VENCIDA
    if conta.data_vencimento == hoje:
        return Situacao.VENCE_HOJE
    return Situacao.A_VENCER


@dataclass(frozen=True)
class FiltroContas:
    situacao: FiltroSituacao = FiltroSituacao.PENDENTES
    de: date | None = None
    ate: date | None = None
    categoria_id: int | None = None
    fornecedor_id: int | None = None
    busca: str | None = None


def _condicoes(restaurante_id: int, filtro: FiltroContas, hoje: date) -> list[ColumnElement[bool]]:
    condicoes = [ContaPagar.restaurante_id == restaurante_id]
    if filtro.situacao == FiltroSituacao.PENDENTES:
        condicoes.append(ContaPagar.data_pagamento.is_(None))
    elif filtro.situacao == FiltroSituacao.VENCIDAS:
        condicoes += [ContaPagar.data_pagamento.is_(None), ContaPagar.data_vencimento < hoje]
    elif filtro.situacao == FiltroSituacao.PAGAS:
        condicoes.append(ContaPagar.data_pagamento.is_not(None))
    if filtro.de:
        condicoes.append(ContaPagar.data_vencimento >= filtro.de)
    if filtro.ate:
        condicoes.append(ContaPagar.data_vencimento <= filtro.ate)
    if filtro.categoria_id:
        condicoes.append(ContaPagar.categoria_id == filtro.categoria_id)
    if filtro.fornecedor_id:
        condicoes.append(ContaPagar.fornecedor_id == filtro.fornecedor_id)
    if filtro.busca:
        condicoes.append(
            or_(
                ContaPagar.descricao.contains(filtro.busca, autoescape=True),
                ContaPagar.numero_documento.contains(filtro.busca, autoescape=True),
            )
        )
    return condicoes


def listar(
    db: Session, restaurante_id: int, filtro: FiltroContas, limite: int, deslocamento: int
) -> tuple[list[ContaPagar], int, Decimal]:
    condicoes = _condicoes(restaurante_id, filtro, tempo.hoje())
    total, valor_total = db.execute(
        select(func.count(ContaPagar.id), func.coalesce(func.sum(ContaPagar.valor), 0)).where(*condicoes)
    ).one()
    # Pendentes: o vencimento mais próximo primeiro. Pagas: o pagamento mais recente primeiro.
    if filtro.situacao == FiltroSituacao.PAGAS:
        ordem = [ContaPagar.data_pagamento.desc(), ContaPagar.id.desc()]
    else:
        ordem = [ContaPagar.data_vencimento, ContaPagar.id]
    contas = db.scalars(select(ContaPagar).where(*condicoes).order_by(*ordem).limit(limite).offset(deslocamento))
    return list(contas.unique()), total, Decimal(valor_total)


def alertas(db: Session, restaurante_id: int, dias: int) -> tuple[date, dict[str, tuple[int, Decimal]]]:
    """Quantidade e valor das contas pendentes vencidas, que vencem hoje e nos próximos `dias`."""
    hoje = tempo.hoje()
    pendente = [ContaPagar.restaurante_id == restaurante_id, ContaPagar.data_pagamento.is_(None)]
    grupos = {
        "vencidas": ContaPagar.data_vencimento < hoje,
        "vencem_hoje": ContaPagar.data_vencimento == hoje,
        "proximos_dias": ContaPagar.data_vencimento.between(hoje + timedelta(days=1), hoje + timedelta(days=dias)),
    }
    resultado = {}
    for nome, condicao in grupos.items():
        quantidade, valor = db.execute(
            select(func.count(ContaPagar.id), func.coalesce(func.sum(ContaPagar.valor), 0)).where(*pendente, condicao)
        ).one()
        resultado[nome] = (quantidade, Decimal(valor))
    return hoje, resultado


def obter(db: Session, restaurante_id: int, conta_id: int) -> ContaPagar | None:
    return db.scalar(select(ContaPagar).where(ContaPagar.id == conta_id, ContaPagar.restaurante_id == restaurante_id))


def novo(db: Session, restaurante_id: int, usuario_id: int, dados: ContaPagarCreate) -> ContaPagar:
    """Valida e adiciona à sessão sem commit, para quem precisa gravar junto com outra mudança."""
    referencias.validar(db, restaurante_id, dados.categoria_id, dados.fornecedor_id)
    conta = ContaPagar(restaurante_id=restaurante_id, criado_por_id=usuario_id, **dados.model_dump())
    db.add(conta)
    db.flush()  # gera o id
    return conta


def criar(db: Session, restaurante_id: int, usuario_id: int, dados: ContaPagarCreate) -> ContaPagar:
    conta = novo(db, restaurante_id, usuario_id, dados)
    db.commit()
    db.refresh(conta)
    return conta


def _garantir_pendente(conta: ContaPagar) -> None:
    if conta.data_pagamento is not None:
        raise OperacaoNaoPermitidaError("Esta conta já foi paga. Desfaça o pagamento para alterá-la.")


def atualizar(db: Session, conta: ContaPagar, dados: ContaPagarCreate) -> ContaPagar:
    _garantir_pendente(conta)
    referencias.validar(
        db,
        conta.restaurante_id,
        dados.categoria_id,
        dados.fornecedor_id,
        categoria_atual=conta.categoria_id,
        fornecedor_atual=conta.fornecedor_id,
    )
    for campo, valor in dados.model_dump().items():
        setattr(conta, campo, valor)
    db.commit()
    db.refresh(conta)
    return conta


def excluir(db: Session, conta: ContaPagar) -> None:
    _garantir_pendente(conta)
    db.delete(conta)
    db.commit()


def pagar(db: Session, conta: ContaPagar, usuario_id: int, data_pagamento: date | None) -> ContaPagar:
    """Marca como paga e cria a despesa correspondente, na mesma transação."""
    # Trava a linha até o commit: um segundo pedido simultâneo espera e já encontra a conta paga.
    db.refresh(conta, with_for_update=True)
    _garantir_pendente(conta)
    data_pagamento = data_pagamento or tempo.hoje()
    if data_pagamento > tempo.hoje():
        raise OperacaoNaoPermitidaError("A data de pagamento não pode estar no futuro.")

    conta.data_pagamento = data_pagamento
    conta.despesa = Despesa(
        restaurante_id=conta.restaurante_id,
        descricao=conta.descricao,
        valor=conta.valor,
        data=data_pagamento,
        categoria_id=conta.categoria_id,
        fornecedor_id=conta.fornecedor_id,
        numero_documento=conta.numero_documento,
        observacoes=conta.observacoes,
        criado_por_id=usuario_id,
    )
    db.commit()
    db.refresh(conta)
    return conta


def desfazer_pagamento(db: Session, conta: ContaPagar) -> ContaPagar:
    """Volta a conta para pendente e remove a despesa que o pagamento havia gerado."""
    db.refresh(conta, with_for_update=True)
    if conta.data_pagamento is None:
        raise OperacaoNaoPermitidaError("Esta conta não está paga.")
    if conta.despesa is not None:
        db.delete(conta.despesa)
    conta.data_pagamento = None
    db.commit()
    db.refresh(conta)
    return conta
