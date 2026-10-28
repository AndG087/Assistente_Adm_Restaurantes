"""Transforma a pergunta em um PLANO de consulta, escolhido entre consultas pré-definidas.

Primeiro por regras fixas (previsíveis e testáveis). A IA só entra quando as regras não
reconhecem a pergunta, e mesmo assim só pode escolher entre as mesmas consultas.
"""

import re
from dataclasses import dataclass
from datetime import date

from app.models import CategoriaFinanceira, Fornecedor
from app.services import palavras_chave
from app.services.assistente import periodo as periodos
from app.services.assistente.periodo import Periodo

CONSULTAS = {
    "total_despesas": "Total de despesas",
    "despesas_por_categoria": "Despesas por categoria",
    "maiores_despesas": "Maiores despesas",
    "despesas_por_fornecedor": "Despesas por fornecedor",
    "comparar_periodos": "Comparação com o período anterior",
    "contas_vencidas": "Contas vencidas",
    "contas_a_vencer": "Contas a vencer",
}


@dataclass(frozen=True)
class Plano:
    consulta: str
    periodo: Periodo
    categoria: CategoriaFinanceira | None = None
    fornecedor: Fornecedor | None = None
    dias: int = 7  # horizonte de "contas a vencer"


# Palavras que indicam uma pergunta sobre as finanças (usadas para decidir se vale consultar a IA).
_ASSUNTO_FINANCEIRO = re.compile(
    r"gast|despes|custo|conta|pag|fornecedor|categori|valor|dinheiro|compr|boleto|nota|r\$|quanto|total|venc"
)


def parece_financeira(texto: str) -> bool:
    return bool(_ASSUNTO_FINANCEIRO.search(palavras_chave.normalizar(texto)))


def _dias_de_horizonte(texto: str) -> int:
    if m := re.search(r"\b(\d{1,3})\s+dias\b", texto):
        return max(1, min(int(m.group(1)), 90))
    if re.search(r"\bmes\b", texto):
        return 30
    if re.search(r"\bhoje\b", texto):
        return 0
    return 7


def _encontrar_por_nome(texto: str, itens: list) -> object | None:
    # Nome mais longo primeiro: "Água e esgoto" antes de "Água".
    for item in sorted(itens, key=lambda i: len(i.nome), reverse=True):
        nome = palavras_chave.normalizar(item.nome).strip()
        if len(nome) >= 3 and re.search(rf"\b{re.escape(nome)}s?\b", texto):
            return item
    return None


def _categoria(texto: str, original: str, categorias: list[CategoriaFinanceira]) -> CategoriaFinanceira | None:
    if encontrada := _encontrar_por_nome(texto, categorias):
        return encontrada
    # "quanto gastei com cerveja" → Bebidas, pelas mesmas palavras-chave da sugestão de categoria.
    por_nome = {palavras_chave.chave_de_nome(c.nome): c for c in categorias}
    reconhecida = palavras_chave.reconhecer(original, set(por_nome))
    return por_nome[palavras_chave.chave_de_nome(reconhecida.categoria)] if reconhecida else None


def interpretar(
    pergunta: str,
    categorias: list[CategoriaFinanceira],
    fornecedores: list[Fornecedor],
    hoje: date,
) -> Plano | None:
    texto = palavras_chave.normalizar(pergunta)
    periodo = periodos.interpretar(texto, hoje) or periodos.este_mes(hoje)

    if re.search(r"vencid|atrasad|em atraso", texto):
        return Plano("contas_vencidas", periodo)
    if re.search(r"\bvence|a vencer|vencimento|a pagar|tenho (que|de) pagar|boleto|proximas contas", texto):
        return Plano("contas_a_vencer", periodo, dias=_dias_de_horizonte(texto))

    if not re.search(r"gast|despes|custo|pagu?ei|compr|saiu|saida", texto):
        return None

    if re.search(r"compar|em relacao|versus|\bvs\b|diferenca|aument|diminu|cresc", texto):
        return Plano("comparar_periodos", periodo)
    if re.search(r"maior(es)?|mais car[oa]s?|top \d|principais", texto) and not re.search(r"categori|fornecedor", texto):
        return Plano("maiores_despesas", periodo)
    if re.search(r"por categoria|categorias|onde (eu )?(mais )?gast|com o que (eu )?(mais )?gast|em que (eu )?(mais )?gast", texto):
        return Plano("despesas_por_categoria", periodo)

    fornecedor = _encontrar_por_nome(texto, fornecedores)
    if fornecedor is None and re.search(r"fornecedor", texto):
        return Plano("despesas_por_fornecedor", periodo)
    return Plano(
        "total_despesas", periodo, categoria=_categoria(texto, pergunta, categorias), fornecedor=fornecedor
    )
