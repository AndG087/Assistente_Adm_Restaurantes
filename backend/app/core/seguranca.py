"""Senhas e tokens de sessão, usando apenas a biblioteca padrão do Python."""

import base64
import hashlib
import hmac
import secrets

# Parâmetros do scrypt (recomendação OWASP: N=2^17 é o ideal; 2^14 mantém o login rápido em máquinas modestas).
_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_TAMANHO = 32


def _b64(dados: bytes) -> str:
    return base64.b64encode(dados).decode("ascii")


def _scrypt(senha: str, sal: bytes, n: int, r: int, p: int, tamanho: int) -> bytes:
    return hashlib.scrypt(senha.encode("utf-8"), salt=sal, n=n, r=r, p=p, dklen=tamanho, maxmem=64 * 1024 * 1024)


def gerar_hash_senha(senha: str) -> str:
    """Formato: scrypt$N$r$p$sal$hash. Os parâmetros ficam no próprio hash para permitir ajustá-los no futuro."""
    sal = secrets.token_bytes(16)
    derivada = _scrypt(senha, sal, _SCRYPT_N, _SCRYPT_R, _SCRYPT_P, _SCRYPT_TAMANHO)
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${_b64(sal)}${_b64(derivada)}"


def verificar_senha(senha: str, hash_armazenado: str) -> bool:
    try:
        algoritmo, n, r, p, sal, esperado = hash_armazenado.split("$")
        if algoritmo != "scrypt":
            return False
        esperado_bytes = base64.b64decode(esperado)
        derivada = _scrypt(senha, base64.b64decode(sal), int(n), int(r), int(p), len(esperado_bytes))
    except (ValueError, TypeError):
        return False
    # compare_digest leva o mesmo tempo independentemente de onde os bytes diferem.
    return hmac.compare_digest(derivada, esperado_bytes)


# Hash de uma senha qualquer, usado para gastar o mesmo tempo quando o e-mail não existe.
HASH_FICTICIO = gerar_hash_senha(secrets.token_urlsafe(16))


def gerar_token_sessao() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """O banco guarda só o hash do token: quem ler a tabela não consegue usar as sessões."""
    return hashlib.sha256(token.encode("ascii")).hexdigest()
