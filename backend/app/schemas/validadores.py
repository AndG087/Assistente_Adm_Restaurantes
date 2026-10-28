"""Validações reaproveitadas por vários schemas."""

import re

_PADRAO_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PADRAO_TELEFONE = re.compile(r"^[0-9()+\-\s]{8,20}$")


def somente_digitos(valor: str) -> str:
    return "".join(c for c in valor if c.isdigit())


def texto_limpo(valor: str) -> str:
    """Remove espaços das pontas e espaços repetidos no meio."""
    return " ".join(valor.split())


def opcional(valor: str | None) -> str | None:
    """Converte texto vazio em None."""
    if valor is None:
        return None
    valor = texto_limpo(valor)
    return valor or None


def _digito_verificador(base: str, pesos: list[int]) -> str:
    resto = sum(int(d) * p for d, p in zip(base, pesos, strict=True)) % 11
    return "0" if resto < 2 else str(11 - resto)


def cnpj_valido(digitos: str) -> bool:
    if len(digitos) != 14 or not digitos.isdigit() or len(set(digitos)) == 1:
        return False
    pesos = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    primeiro = _digito_verificador(digitos[:12], pesos[1:])
    segundo = _digito_verificador(digitos[:12] + primeiro, pesos)
    return digitos[12:] == primeiro + segundo


def cpf_valido(digitos: str) -> bool:
    if len(digitos) != 11 or not digitos.isdigit() or len(set(digitos)) == 1:
        return False
    primeiro = _digito_verificador(digitos[:9], list(range(10, 1, -1)))
    segundo = _digito_verificador(digitos[:9] + primeiro, list(range(11, 1, -1)))
    return digitos[9:] == primeiro + segundo


def normalizar_cnpj(valor: str | None) -> str | None:
    if valor is None or not valor.strip():
        return None
    digitos = somente_digitos(valor)
    if not cnpj_valido(digitos):
        raise ValueError("CNPJ inválido.")
    return digitos


def normalizar_documento(valor: str | None) -> str | None:
    """Aceita CPF (11 dígitos) ou CNPJ (14 dígitos), com ou sem pontuação."""
    if valor is None or not valor.strip():
        return None
    digitos = somente_digitos(valor)
    if (len(digitos) == 11 and cpf_valido(digitos)) or (len(digitos) == 14 and cnpj_valido(digitos)):
        return digitos
    raise ValueError("CPF ou CNPJ inválido.")


def normalizar_email(valor: str | None) -> str | None:
    if valor is None or not valor.strip():
        return None
    valor = valor.strip().lower()
    if not _PADRAO_EMAIL.match(valor):
        raise ValueError("E-mail inválido.")
    return valor


def normalizar_telefone(valor: str | None) -> str | None:
    if valor is None or not valor.strip():
        return None
    valor = texto_limpo(valor)
    if not _PADRAO_TELEFONE.match(valor) or len(somente_digitos(valor)) < 8:
        raise ValueError("Telefone inválido.")
    return valor
