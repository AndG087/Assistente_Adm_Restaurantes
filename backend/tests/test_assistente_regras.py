"""Regras que entendem a pergunta (sem banco e sem IA)."""

from datetime import date

import pytest

from app.models import CategoriaFinanceira, Fornecedor
from app.services.assistente import intencao, periodo
from app.services.categoria_service import CATEGORIAS_PADRAO
from app.services.palavras_chave import normalizar

HOJE = date(2026, 10, 20)  # terça-feira
CATEGORIAS = [CategoriaFinanceira(id=i, nome=n, ativo=True) for i, n in enumerate(CATEGORIAS_PADRAO, 1)]
FORNECEDORES = [Fornecedor(id=1, nome="Distribuidora Sul", ativo=True), Fornecedor(id=2, nome="Gás Express", ativo=True)]


@pytest.mark.parametrize(
    ("texto", "de", "ate"),
    [
        ("quanto gastei hoje", "2026-10-20", "2026-10-20"),
        ("e ontem?", "2026-10-19", "2026-10-19"),
        ("gastos desta semana", "2026-10-19", "2026-10-25"),
        ("na semana passada", "2026-10-12", "2026-10-18"),
        ("este mês", "2026-10-01", "2026-10-31"),
        ("mês passado", "2026-09-01", "2026-09-30"),
        ("últimos 15 dias", "2026-10-06", "2026-10-20"),
        ("em setembro", "2026-09-01", "2026-09-30"),
        ("em março de 2025", "2025-03-01", "2025-03-31"),
        # Mês ainda não chegado neste ano: refere-se ao do ano passado.
        ("em dezembro", "2025-12-01", "2025-12-31"),
        ("em 2025", "2025-01-01", "2025-12-31"),
        ("este ano", "2026-01-01", "2026-12-31"),
        ("despesas deste mês", "2026-10-01", "2026-10-31"),
        ("nesta semana", "2026-10-19", "2026-10-25"),
        ("gastos desse ano", "2026-01-01", "2026-12-31"),
    ],
)
def test_periodos(texto, de, ate):
    p = periodo.interpretar(normalizar(texto), HOJE)
    assert (p.de.isoformat(), p.ate.isoformat()) == (de, ate)


def test_sem_periodo_reconhecido():
    assert periodo.interpretar(normalizar("quanto gastei?"), HOJE) is None


def test_periodo_anterior():
    assert periodo.anterior(periodo.mes(2026, 3)).rotulo == "fevereiro de 2026"
    assert periodo.anterior(periodo.mes(2026, 1)).de == date(2025, 12, 1)
    semana = periodo.Periodo(date(2026, 10, 19), date(2026, 10, 25), "esta semana")
    assert periodo.anterior(semana).de == date(2026, 10, 12)


def plano(pergunta):
    return intencao.interpretar(pergunta, CATEGORIAS, FORNECEDORES, HOJE)


@pytest.mark.parametrize(
    ("pergunta", "consulta"),
    [
        ("Quanto gastei este mês?", "total_despesas"),
        ("Qual foi o total de despesas em setembro?", "total_despesas"),
        ("Em que categorias eu mais gastei?", "despesas_por_categoria"),
        ("Despesas por categoria do mês passado", "despesas_por_categoria"),
        ("Quais foram as maiores despesas da semana?", "maiores_despesas"),
        ("Gastos por fornecedor em outubro", "despesas_por_fornecedor"),
        ("Compare os gastos deste mês com o mês passado", "comparar_periodos"),
        ("Tenho contas vencidas?", "contas_vencidas"),
        ("Quais contas estão atrasadas?", "contas_vencidas"),
        ("Quais contas vencem esta semana?", "contas_a_vencer"),
        ("O que tenho a pagar nos próximos 15 dias?", "contas_a_vencer"),
    ],
)
def test_consultas_reconhecidas(pergunta, consulta):
    assert plano(pergunta).consulta == consulta


def test_categoria_pelo_nome_ou_pela_palavra_chave():
    assert plano("Quanto gastei com bebidas em outubro?").categoria.nome == "Bebidas"
    assert plano("Quanto gastei de gás este mês?").categoria.nome == "Gás"
    assert plano("Quanto gastei com cerveja?").categoria.nome == "Bebidas"
    assert plano("Quanto gastei com a conta de luz?").categoria.nome == "Energia elétrica"


def test_fornecedor_pelo_nome():
    p = plano("Quanto gastei com a Distribuidora Sul em setembro?")
    assert p.fornecedor.nome == "Distribuidora Sul"
    assert p.periodo.de == date(2026, 9, 1)
    # "Gás Express" é fornecedor; a categoria Gás não é aplicada junto.
    assert plano("quanto gastei com gás express").fornecedor.nome == "Gás Express"


def test_horizonte_de_contas_a_vencer():
    assert plano("contas a vencer nos próximos 15 dias").dias == 15
    assert plano("o que vence este mês").dias == 30
    assert plano("o que vence hoje").dias == 0
    assert plano("quais boletos vencem").dias == 7


@pytest.mark.parametrize("pergunta", ["Oi, tudo bem?", "Me dê uma receita de bolo", "Como melhorar meu cardápio?"])
def test_perguntas_que_nao_sao_consultas(pergunta):
    assert plano(pergunta) is None
    assert not intencao.parece_financeira(pergunta)
