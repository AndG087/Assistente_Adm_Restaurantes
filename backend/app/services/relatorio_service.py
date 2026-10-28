"""Relatórios: evolução mensal, totais por fornecedor e exportação em CSV.

Todos os valores são somados pelo banco (DECIMAL); nada é estimado.
"""

import csv
import io
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import extract, func, select
from sqlalchemy.orm import Session

from app.models import Despesa, Fornecedor
from app.services import conta_pagar_service, despesa_service
from app.services.conta_pagar_service import FiltroContas
from app.services.despesa_service import FiltroDespesas

MESES_ABREVIADOS = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


@dataclass(frozen=True)
class TotalMes:
    ano: int
    mes: int
    quantidade: int
    valor: Decimal

    @property
    def rotulo(self) -> str:
        return f"{MESES_ABREVIADOS[self.mes - 1]}/{self.ano}"


def _meses_ate(hoje: date, quantidade: int) -> list[tuple[int, int]]:
    """(ano, mês) dos `quantidade` meses terminando no mês de hoje, do mais antigo para o mais recente."""
    atual = hoje.year * 12 + (hoje.month - 1)
    return [(i // 12, i % 12 + 1) for i in range(atual - quantidade + 1, atual + 1)]


def _primeiro_dia_do_proximo_mes(hoje: date) -> date:
    return date(hoje.year + 1, 1, 1) if hoje.month == 12 else date(hoje.year, hoje.month + 1, 1)


def evolucao_mensal(db: Session, restaurante_id: int, hoje: date, meses: int) -> list[TotalMes]:
    lista = _meses_ate(hoje, meses)
    ano_inicio, mes_inicio = lista[0]
    ano = extract("year", Despesa.data)
    mes = extract("month", Despesa.data)
    linhas = db.execute(
        select(ano, mes, func.count(Despesa.id), func.sum(Despesa.valor))
        .where(
            Despesa.restaurante_id == restaurante_id,
            Despesa.data >= date(ano_inicio, mes_inicio, 1),
            Despesa.data < _primeiro_dia_do_proximo_mes(hoje),
        )
        .group_by(ano, mes)
    ).all()
    por_mes = {(int(a), int(m)): (quantidade, Decimal(valor)) for a, m, quantidade, valor in linhas}
    # Meses sem despesas aparecem com zero: um buraco no gráfico esconderia a informação.
    return [TotalMes(a, m, *por_mes.get((a, m), (0, Decimal(0)))) for a, m in lista]


def por_fornecedor(
    db: Session, restaurante_id: int, de: date | None, ate: date | None, limite: int = 10
) -> list[tuple[Fornecedor | None, int, Decimal]]:
    """Total por fornecedor no período, do maior para o menor; sem fornecedor aparece como None."""
    soma = func.sum(Despesa.valor)
    consulta = select(Despesa.fornecedor_id, func.count(Despesa.id), soma).where(
        Despesa.restaurante_id == restaurante_id
    )
    if de:
        consulta = consulta.where(Despesa.data >= de)
    if ate:
        consulta = consulta.where(Despesa.data <= ate)
    linhas = db.execute(consulta.group_by(Despesa.fornecedor_id).order_by(soma.desc()).limit(limite)).all()
    ids = [fid for fid, _, _ in linhas if fid is not None]
    fornecedores = {f.id: f for f in db.scalars(select(Fornecedor).where(Fornecedor.id.in_(ids)))}
    return [(fornecedores.get(fid) if fid else None, q, Decimal(v)) for fid, q, v in linhas]


# --- CSV ---


def _celula(valor: object) -> str:
    """Protege contra injeção de fórmulas: o Excel executaria um texto que começa com = + - @."""
    texto = "" if valor is None else str(valor)
    return f"'{texto}" if texto[:1] in ("=", "+", "-", "@", "\t", "\r") else texto


def _dinheiro(valor: Decimal) -> str:
    return f"{valor:.2f}".replace(".", ",")


def _data(valor: date | None) -> str:
    return valor.strftime("%d/%m/%Y") if valor else ""


def _csv(cabecalho: list[str], linhas: Iterator[list[object]]) -> str:
    saida = io.StringIO()
    # Ponto e vírgula e vírgula decimal: o Excel em português abre o arquivo direto, sem importação.
    escritor = csv.writer(saida, delimiter=";", lineterminator="\r\n")
    escritor.writerow(cabecalho)
    for linha in linhas:
        escritor.writerow([_celula(c) for c in linha])
    # BOM: faz o Excel reconhecer UTF-8 (acentos corretos).
    return "﻿" + saida.getvalue()


def _todas(listar, *argumentos) -> Iterator:
    """Percorre todas as páginas de uma listagem (os serviços limitam o tamanho de cada página)."""
    deslocamento = 0
    while True:
        itens, total, _ = listar(*argumentos, 200, deslocamento)
        yield from itens
        deslocamento += len(itens)
        if not itens or deslocamento >= total:
            return


def despesas_csv(db: Session, restaurante_id: int, filtro: FiltroDespesas) -> str:
    def linhas() -> Iterator[list[object]]:
        for d in _todas(despesa_service.listar, db, restaurante_id, filtro):
            yield [
                _data(d.data), d.descricao, d.categoria.nome if d.categoria else "",
                d.fornecedor.nome if d.fornecedor else "", d.numero_documento, _dinheiro(d.valor), d.observacoes,
            ]

    return _csv(["Data", "Descrição", "Categoria", "Fornecedor", "Nº documento", "Valor (R$)", "Observações"], linhas())


def contas_csv(db: Session, restaurante_id: int, filtro: FiltroContas, hoje: date) -> str:
    situacoes = {"paga": "Paga", "vencida": "Vencida", "vence_hoje": "Vence hoje", "a_vencer": "A vencer"}

    def linhas() -> Iterator[list[object]]:
        for c in _todas(conta_pagar_service.listar, db, restaurante_id, filtro):
            yield [
                _data(c.data_vencimento), c.descricao, c.categoria.nome if c.categoria else "",
                c.fornecedor.nome if c.fornecedor else "", c.numero_documento, _dinheiro(c.valor),
                situacoes[conta_pagar_service.situacao(c, hoje)], _data(c.data_pagamento),
            ]

    cabecalho = ["Vencimento", "Descrição", "Categoria", "Fornecedor", "Nº documento", "Valor (R$)", "Situação",
                 "Pagamento"]
    return _csv(cabecalho, linhas())

