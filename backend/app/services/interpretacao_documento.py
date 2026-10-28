"""Interpretação do texto extraído por REGRAS FIXAS (expressões regulares), sem IA.

Encontra valor total, datas, CNPJ do emitente, número do documento e chave de acesso da NF-e.
O resultado são sugestões para a tela de conferência: o usuário sempre revisa antes de salvar.
"""

import re
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from app.schemas.validadores import cnpj_valido, somente_digitos

# 1.234,56 ou 1234,56 (formato brasileiro; exige os centavos para não confundir com outros números)
_DINHEIRO = r"(\d{1,3}(?:\.\d{3})+,\d{2}|\d+,\d{2})"
_RE_DINHEIRO = re.compile(_DINHEIRO)
_RE_DATA = re.compile(r"\b(\d{2})[/.-](\d{2})[/.-](\d{4})\b")
_RE_CNPJ = re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b")
# Chave de acesso: 44 dígitos, muitas vezes em grupos de 4 separados por espaço.
_RE_CHAVE = re.compile(r"(?<!\d)(\d{4}(?:\s?\d{4}){10})(?!\d)")

# Rótulos que precedem o valor a pagar, do mais para o menos específico.
_ROTULOS_TOTAL = [
    r"valor\s+total\s+da\s+nota",
    r"valor\s+total\s+a\s+pagar",
    r"total\s+a\s+pagar",
    r"valor\s+a\s+pagar",
    r"valor\s+do\s+documento",
    r"valor\s+cobrado",
    r"valor\s+total",
    r"total\s+geral",
    r"total\s+r\$",
    r"\btotal\b",
]
_RE_VENCIMENTO = re.compile(r"vencimento|vencto|data\s+limite", re.IGNORECASE)
_RE_EMISSAO = re.compile(r"emiss[aã]o|data\s+de\s+sa[ií]da|data\s+do\s+documento", re.IGNORECASE)
# "NF-e Nº 4521", "Nota Fiscal N 004521", "Número do documento: 4521"...
_RE_NUMERO = re.compile(
    r"(?:\bnf-?e\b|nota\s+fiscal|\bdanfe\b|n[ºo°.]\s*do\s+documento|n[úu]mero\s+do\s+documento|\bn[º°o]\.?)"
    r"\s*[:\-]?\s*(?:(?:n[úu]mero|n[º°o.]?)\s*[:\-]?\s*)?(\d[\d.]{0,14}\d|\d)\b",
    re.IGNORECASE,
)
_RE_BOLETO = re.compile(r"linha\s+digit[aá]vel|boleto|benefici[aá]rio|cedente|ficha\s+de\s+compensa", re.IGNORECASE)


def _dinheiro(texto: str) -> Decimal | None:
    try:
        return Decimal(texto.replace(".", "").replace(",", "."))
    except InvalidOperation:
        return None


def _data(dia: str, mes: str, ano: str) -> date | None:
    try:
        data = date(int(ano), int(mes), int(dia))
    except ValueError:
        return None
    return data if 2000 <= data.year <= 2100 else None


def _datas_na_linha(linha: str) -> list[date]:
    return [d for d in (_data(*m.groups()) for m in _RE_DATA.finditer(linha)) if d]


def _valor_total(linhas: list[str]) -> Decimal | None:
    for rotulo in _ROTULOS_TOTAL:
        padrao = re.compile(rotulo, re.IGNORECASE)
        for i, linha in enumerate(linhas):
            encontrado = padrao.search(linha)
            if not encontrado:
                continue
            # O valor costuma estar na mesma linha, depois do rótulo, ou na linha seguinte.
            for trecho in (linha[encontrado.end() :], *linhas[i + 1 : i + 3]):
                valores = [v for v in (_dinheiro(m) for m in _RE_DINHEIRO.findall(trecho)) if v and v > 0]
                if valores:
                    return valores[0]
    # Sem rótulo reconhecido: o maior valor monetário do documento é o candidato mais provável.
    todos = [v for v in (_dinheiro(m) for linha in linhas for m in _RE_DINHEIRO.findall(linha)) if v and v > 0]
    return max(todos) if todos else None


def _data_rotulada(linhas: list[str], rotulo: re.Pattern[str]) -> date | None:
    for i, linha in enumerate(linhas):
        encontrado = rotulo.search(linha)
        if not encontrado:
            continue
        for trecho in (linha[encontrado.end() :], *linhas[i + 1 : i + 3]):
            datas = _datas_na_linha(trecho)
            if datas:
                return datas[0]
    return None


def _cnpjs(texto: str) -> list[str]:
    encontrados = []
    for m in _RE_CNPJ.finditer(texto):
        digitos = somente_digitos(m.group())
        if len(digitos) == 14 and cnpj_valido(digitos) and digitos not in encontrados:
            encontrados.append(digitos)
    return encontrados


def _chave_acesso(texto: str) -> str | None:
    for m in _RE_CHAVE.finditer(texto):
        digitos = somente_digitos(m.group(1))
        # A chave contém o CNPJ do emitente nas posições 7 a 20.
        if len(digitos) == 44 and cnpj_valido(digitos[6:20]):
            return digitos
    return None


def interpretar(texto: str, cnpj_do_restaurante: str | None = None) -> dict[str, Any]:
    """Campos sugeridos, em formato JSON (datas ISO, valor como texto "1234.50")."""
    linhas = [linha.strip() for linha in texto.splitlines() if linha.strip()]

    valor = _valor_total(linhas)
    vencimento = _data_rotulada(linhas, _RE_VENCIMENTO)
    emissao = _data_rotulada(linhas, _RE_EMISSAO)
    todas_as_datas = [d for linha in linhas for d in _datas_na_linha(linha)]
    if emissao is None and todas_as_datas:
        emissao = todas_as_datas[0]

    chave = _chave_acesso(texto)
    # O CNPJ do próprio restaurante aparece como destinatário/pagador: não é o fornecedor.
    cnpjs = [c for c in _cnpjs(texto) if c != cnpj_do_restaurante]
    cnpj_emitente = chave[6:20] if chave else (cnpjs[0] if cnpjs else None)

    numero = None
    if chave:
        numero = str(int(chave[25:34]))  # número da NF-e, posições 26 a 34 da chave
    else:
        m = _RE_NUMERO.search(texto)
        if m:
            numero = m.group(1).replace(".", "").lstrip("0") or "0"

    parece_boleto = bool(_RE_BOLETO.search(texto))
    tipo = "conta" if (vencimento is not None or parece_boleto) else "despesa"

    return {
        "valor": f"{valor:.2f}" if valor is not None else None,
        "data_emissao": emissao.isoformat() if emissao else None,
        "data_vencimento": vencimento.isoformat() if vencimento else None,
        "cnpj_emitente": cnpj_emitente,
        "numero_documento": numero,
        "chave_acesso": chave,
        "tipo_sugerido": tipo,
    }
