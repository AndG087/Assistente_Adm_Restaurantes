"""Interpretação de períodos em português, sempre relativa a "hoje" (data do computador)."""

import calendar
import re
from dataclasses import dataclass
from datetime import date, timedelta

MESES = {
    "janeiro": 1, "fevereiro": 2, "marco": 3, "abril": 4, "maio": 5, "junho": 6,
    "julho": 7, "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12,
}
NOMES_MESES = {numero: nome for nome, numero in MESES.items()} | {3: "março"}


@dataclass(frozen=True)
class Periodo:
    de: date
    ate: date
    rotulo: str  # ex.: "outubro de 2026", "hoje", "últimos 15 dias"

    @property
    def mes_inteiro(self) -> bool:
        return self.de.day == 1 and self.ate == _fim_do_mes(self.de.year, self.de.month)


def _fim_do_mes(ano: int, mes: int) -> date:
    return date(ano, mes, calendar.monthrange(ano, mes)[1])


def mes(ano: int, numero: int) -> Periodo:
    return Periodo(date(ano, numero, 1), _fim_do_mes(ano, numero), f"{NOMES_MESES[numero]} de {ano}")


def este_mes(hoje: date) -> Periodo:
    return mes(hoje.year, hoje.month)


def anterior(periodo: Periodo) -> Periodo:
    """Período de mesma duração imediatamente antes (para meses inteiros, o mês anterior)."""
    if periodo.mes_inteiro:
        dia = periodo.de - timedelta(days=1)
        return mes(dia.year, dia.month)
    duracao = periodo.ate - periodo.de
    ate = periodo.de - timedelta(days=1)
    return Periodo(ate - duracao, ate, "período anterior")


def por_nome(nome: str, hoje: date) -> Periodo:
    """Períodos nomeados usados pela classificação da IA."""
    segunda = hoje - timedelta(days=hoje.weekday())
    mes_passado = hoje.replace(day=1) - timedelta(days=1)
    nomes = {
        "hoje": lambda: Periodo(hoje, hoje, "hoje"),
        "ontem": lambda: Periodo(hoje - timedelta(days=1), hoje - timedelta(days=1), "ontem"),
        "esta_semana": lambda: Periodo(segunda, segunda + timedelta(days=6), "esta semana"),
        "semana_passada": lambda: Periodo(segunda - timedelta(days=7), segunda - timedelta(days=1), "semana passada"),
        "mes_passado": lambda: mes(mes_passado.year, mes_passado.month),
        "este_ano": lambda: Periodo(date(hoje.year, 1, 1), date(hoje.year, 12, 31), f"{hoje.year}"),
        "ano_passado": lambda: Periodo(date(hoje.year - 1, 1, 1), date(hoje.year - 1, 12, 31), f"{hoje.year - 1}"),
        "ultimos_30_dias": lambda: Periodo(hoje - timedelta(days=29), hoje, "últimos 30 dias"),
    }
    return nomes.get(nome, lambda: este_mes(hoje))()


def interpretar(texto: str, hoje: date) -> Periodo | None:
    """Encontra o período na pergunta (texto já normalizado: minúsculo e sem acentos)."""
    if m := re.search(r"\bultimos?\s+(\d{1,3})\s+dias\b", texto):
        dias = max(1, min(int(m.group(1)), 366))
        return Periodo(hoje - timedelta(days=dias - 1), hoje, f"últimos {dias} dias")
    if re.search(r"\bhoje\b", texto):
        return por_nome("hoje", hoje)
    if re.search(r"\bontem\b", texto):
        return por_nome("ontem", hoje)
    if re.search(r"\bsemana passada\b|\bultima semana\b", texto):
        return por_nome("semana_passada", hoje)
    if re.search(r"\b[dn]?(esta|essa) semana\b|\bsemana atual\b", texto):
        return por_nome("esta_semana", hoje)
    if re.search(r"\bmes passado\b|\bultimo mes\b|\bmes anterior\b", texto):
        return por_nome("mes_passado", hoje)
    if re.search(r"\bano passado\b|\bultimo ano\b", texto):
        return por_nome("ano_passado", hoje)
    if re.search(r"\b[dn]?(este|esse) ano\b|\bano atual\b", texto):
        return por_nome("este_ano", hoje)

    for nome, numero in MESES.items():
        if m := re.search(rf"\b{nome}(?:\s+de)?(?:\s+(20\d\d))?\b", texto):
            if m.group(1):
                ano = int(m.group(1))
            else:
                # "outubro" perguntado em fevereiro se refere ao outubro passado.
                ano = hoje.year if numero <= hoje.month else hoje.year - 1
            return mes(ano, numero)

    if m := re.search(r"\b(?:em|de|no ano de)\s+(20\d\d)\b", texto):
        ano = int(m.group(1))
        return Periodo(date(ano, 1, 1), date(ano, 12, 31), str(ano))
    if re.search(r"\b[dn]?(este|esse) mes\b|\bmes atual\b|\bno mes\b", texto):
        return este_mes(hoje)
    return None
