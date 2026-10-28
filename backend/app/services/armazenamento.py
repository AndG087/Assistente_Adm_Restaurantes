"""Arquivos de documentos no disco local.

Os nomes são gerados aqui (uuid); o nome enviado pelo usuário nunca vira caminho,
o que impede gravar ou ler fora da pasta (ex.: "../../config.py").
"""

import uuid
from pathlib import Path

from app.core.config import get_settings


def _base() -> Path:
    return get_settings().documentos_dir.resolve()


def caminho(arquivo: str) -> Path:
    """Caminho absoluto de um arquivo salvo, garantindo que ele está dentro da pasta de documentos."""
    base = _base()
    destino = (base / arquivo).resolve()
    if not destino.is_relative_to(base):
        raise ValueError("Caminho de documento inválido.")
    return destino


def salvar(restaurante_id: int, conteudo: bytes, extensao: str) -> str:
    arquivo = f"{restaurante_id}/{uuid.uuid4().hex}{extensao}"
    destino = caminho(arquivo)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(conteudo)
    return arquivo


def ler(arquivo: str) -> bytes:
    return caminho(arquivo).read_bytes()


def remover(arquivo: str) -> None:
    caminho(arquivo).unlink(missing_ok=True)
