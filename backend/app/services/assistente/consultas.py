"""Executa um plano de consulta e monta a resposta em texto, com valores calculados pelo banco.

As frases são modelos fixos: nenhum número passa pela IA.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import ContaPagar, Despesa, Fornecedor
from app.services import despesa_service
from app.services.assistente import periodo as periodos
from app.services.assistente.intencao import CONSULTAS, Plano
from app.services.despesa_service import FiltroDespesas

_LIMITE_LINHAS = 10


@dataclass(frozen=True)
class Tabela:
    colunas: list[str]
    linhas: list[list[str]]


@dataclass(frozen=True)
class Resultado:
    texto: str
    consulta: str  # descrição legível do que foi consultado
    tabela: Tabela | None = field(default=None)


def moeda(valor: Decimal | int) -> str:
    """1234.5 → "R$ 1.234,50"."""
    texto = f"{Decimal(valor):,.2f}"
    return "R$ " + texto.replace(",", "_").replace(".", ",").replace("_", ".")


def data_br(dia: date) -> str:
    return dia.strftime("%d/%m/%Y")


def _intervalo(plano: Plano) -> str:
    p = plano.periodo
    return data_br(p.de) if p.de == p.ate else f"{data_br(p.de)} a {data_br(p.ate)}"


def _preposicao(rotulo: str) -> str:
    """ "últimos 7 dias" → "nos últimos 7 dias", "outubro de 2026" → "em outubro de 2026"... """
    if rotulo.startswith("últimos"):
        return f"nos {rotulo}"
    if rotulo in ("hoje", "ontem"):
        return rotulo
    especiais = {"esta semana": "nesta semana", "semana passada": "na semana passada", "período anterior": "no período anterior"}
    return especiais.get(rotulo, f"em {rotulo}")


def _quando(plano: Plano) -> str:
    """Ex.: "nos últimos 7 dias (21/10/2026 a 27/10/2026)"."""
    return f"{_preposicao(plano.periodo.rotulo)} ({_intervalo(plano)})"


def _maiuscula(texto: str) -> str:
    return texto[0].upper() + texto[1:]


def _plural(quantidade: int, singular: str, plural: str) -> str:
    return f"{quantidade} {singular if quantidade == 1 else plural}"


def executar(db: Session, restaurante_id: int, plano: Plano, hoje: date) -> Resultado:
    consulta = f"{CONSULTAS[plano.consulta]} · {_intervalo(plano)}"
    match plano.consulta:
        case "contas_vencidas":
            return _contas_vencidas(db, restaurante_id, hoje)
        case "contas_a_vencer":
            return _contas_a_vencer(db, restaurante_id, hoje, plano.dias)
        case "despesas_por_categoria":
            return _por_categoria(db, restaurante_id, plano, consulta)
        case "maiores_despesas":
            return _maiores(db, restaurante_id, plano, consulta)
        case "despesas_por_fornecedor":
            return _por_fornecedor(db, restaurante_id, plano, consulta)
        case "comparar_periodos":
            return _comparar(db, restaurante_id, plano)
        case _:
            return _total(db, restaurante_id, plano, consulta)


def _somar(db: Session, restaurante_id: int, filtro: FiltroDespesas) -> tuple[int, Decimal]:
    _, total, valor = despesa_service.listar(db, restaurante_id, filtro, limite=1, deslocamento=0)
    return total, valor


def _total(db: Session, restaurante_id: int, plano: Plano, consulta: str) -> Resultado:
    filtro = FiltroDespesas(
        de=plano.periodo.de,
        ate=plano.periodo.ate,
        categoria_id=plano.categoria.id if plano.categoria else None,
        fornecedor_id=plano.fornecedor.id if plano.fornecedor else None,
    )
    quantidade, valor = _somar(db, restaurante_id, filtro)
    recorte = ""
    if plano.categoria:
        recorte += f" na categoria {plano.categoria.nome}"
        consulta += f" · {plano.categoria.nome}"
    if plano.fornecedor:
        recorte += f" com o fornecedor {plano.fornecedor.nome}"
        consulta += f" · {plano.fornecedor.nome}"
    if quantidade == 0:
        return Resultado(f"Não há despesas registradas{recorte} {_quando(plano)}.", consulta)
    texto = (
        f"{_maiuscula(_quando(plano))}, as despesas{recorte} somaram {moeda(valor)} "
        f"em {_plural(quantidade, 'lançamento', 'lançamentos')}."
    )
    return Resultado(texto, consulta)


def _por_categoria(db: Session, restaurante_id: int, plano: Plano, consulta: str) -> Resultado:
    linhas = despesa_service.resumo_por_categoria(db, restaurante_id, plano.periodo.de, plano.periodo.ate)
    if not linhas:
        return Resultado(f"Não há despesas registradas {_quando(plano)}.", consulta)
    total = sum((valor for _, _, valor in linhas), Decimal(0))
    tabela = Tabela(
        ["Categoria", "Valor", "% do total"],
        [
            [c.nome if c else "Sem categoria", moeda(valor), f"{valor / total * 100:.1f}%".replace(".", ",")]
            for c, _, valor in linhas[:_LIMITE_LINHAS]
        ],
    )
    principal = linhas[0][0].nome if linhas[0][0] else "Sem categoria"
    texto = (
        f"{_maiuscula(_quando(plano))}, as despesas somaram {moeda(total)}. "
        f"A categoria com mais gastos foi {principal} ({moeda(linhas[0][2])})."
    )
    return Resultado(texto, consulta, tabela)


def _maiores(db: Session, restaurante_id: int, plano: Plano, consulta: str) -> Resultado:
    despesas = list(
        db.scalars(
            select(Despesa)
            .where(
                Despesa.restaurante_id == restaurante_id,
                Despesa.data.between(plano.periodo.de, plano.periodo.ate),
            )
            .order_by(Despesa.valor.desc(), Despesa.data.desc())
            .limit(5)
        )
    )
    if not despesas:
        return Resultado(f"Não há despesas registradas {_quando(plano)}.", consulta)
    tabela = Tabela(
        ["Data", "Descrição", "Valor"],
        [[data_br(d.data), d.descricao, moeda(d.valor)] for d in despesas],
    )
    texto = f"As {_plural(len(despesas), 'maior despesa', 'maiores despesas')} {_quando(plano)}:"
    if len(despesas) == 1:
        texto = f"A maior despesa {_quando(plano)}:"
    return Resultado(texto, consulta, tabela)


def _por_fornecedor(db: Session, restaurante_id: int, plano: Plano, consulta: str) -> Resultado:
    soma = func.sum(Despesa.valor)
    linhas = db.execute(
        select(Fornecedor.nome, func.count(Despesa.id), soma)
        .join(Fornecedor, Despesa.fornecedor_id == Fornecedor.id)
        .where(
            Despesa.restaurante_id == restaurante_id,
            Despesa.data.between(plano.periodo.de, plano.periodo.ate),
        )
        .group_by(Fornecedor.id, Fornecedor.nome)
        .order_by(soma.desc())
        .limit(_LIMITE_LINHAS)
    ).all()
    if not linhas:
        return Resultado(f"Não há despesas com fornecedor informado {_quando(plano)}.", consulta)
    tabela = Tabela(
        ["Fornecedor", "Lançamentos", "Valor"],
        [[nome, str(quantidade), moeda(valor)] for nome, quantidade, valor in linhas],
    )
    nome, _, valor = linhas[0]
    texto = f"{_maiuscula(_quando(plano))}, o fornecedor com mais gastos foi {nome} ({moeda(valor)})."
    return Resultado(texto, consulta, tabela)


def _comparar(db: Session, restaurante_id: int, plano: Plano) -> Resultado:
    atual = plano.periodo
    antes = periodos.anterior(atual)
    _, valor_atual = _somar(db, restaurante_id, FiltroDespesas(de=atual.de, ate=atual.ate))
    _, valor_antes = _somar(db, restaurante_id, FiltroDespesas(de=antes.de, ate=antes.ate))
    consulta = f"{CONSULTAS['comparar_periodos']} · {data_br(atual.de)} a {data_br(atual.ate)}"
    diferenca = valor_atual - valor_antes
    texto = (
        f"{_maiuscula(_preposicao(atual.rotulo))}, as despesas somaram {moeda(valor_atual)}; "
        f"{_preposicao(antes.rotulo)} ({data_br(antes.de)} a {data_br(antes.ate)}), {moeda(valor_antes)}. "
    )
    if valor_antes == 0:
        texto += "Não há gastos no período anterior para calcular a variação."
    else:
        percentual = f"{abs(diferenca) / valor_antes * 100:.1f}".replace(".", ",")
        sentido = "a mais" if diferenca > 0 else "a menos"
        texto += (
            "Os gastos ficaram iguais." if diferenca == 0
            else f"Diferença: {moeda(abs(diferenca))} {sentido} ({percentual}%)."
        )
    return Resultado(texto, consulta)


def _tabela_de_contas(contas: list[ContaPagar]) -> Tabela:
    return Tabela(
        ["Vencimento", "Descrição", "Valor"],
        [[data_br(c.data_vencimento), c.descricao, moeda(c.valor)] for c in contas[:_LIMITE_LINHAS]],
    )


def _contas_pendentes(db: Session, restaurante_id: int, *condicoes) -> tuple[list[ContaPagar], Decimal]:
    contas = list(
        db.scalars(
            select(ContaPagar)
            .where(ContaPagar.restaurante_id == restaurante_id, ContaPagar.data_pagamento.is_(None), *condicoes)
            .order_by(ContaPagar.data_vencimento, ContaPagar.id)
        ).unique()
    )
    return contas, sum((c.valor for c in contas), Decimal(0))


def _contas_vencidas(db: Session, restaurante_id: int, hoje: date) -> Resultado:
    contas, total = _contas_pendentes(db, restaurante_id, ContaPagar.data_vencimento < hoje)
    consulta = f"{CONSULTAS['contas_vencidas']} · até {data_br(hoje - timedelta(days=1))}"
    if not contas:
        return Resultado("Não há contas vencidas.", consulta)
    texto = f"Há {_plural(len(contas), 'conta vencida', 'contas vencidas')}, somando {moeda(total)}:"
    return Resultado(texto, consulta, _tabela_de_contas(contas))


def _contas_a_vencer(db: Session, restaurante_id: int, hoje: date, dias: int) -> Resultado:
    limite = hoje + timedelta(days=dias)
    contas, total = _contas_pendentes(db, restaurante_id, ContaPagar.data_vencimento.between(hoje, limite))
    janela = "hoje" if dias == 0 else f"de hoje até {data_br(limite)}"
    consulta = f"{CONSULTAS['contas_a_vencer']} · {data_br(hoje)} a {data_br(limite)}"
    if not contas:
        return Resultado(f"Nenhuma conta pendente vence {janela}.", consulta)
    texto = f"{_plural(len(contas), 'conta vence', 'contas vencem')} {janela}, somando {moeda(total)}:"
    return Resultado(_maiuscula(texto), consulta, _tabela_de_contas(contas))
