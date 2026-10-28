"""Configurações da aplicação, lidas de variáveis de ambiente ou do arquivo backend/.env."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Restaurante Admin AI"

    # Banco de dados local. A senha real fica apenas no .env.
    database_url: str = "mysql+pymysql://restaurante_app@localhost:3306/restaurante_admin"
    # Banco exclusivo dos testes automatizados; é apagado e recriado a cada execução.
    test_database_url: str | None = None

    # Documentos enviados (notas, boletos, comprovantes). Ficam só neste computador.
    documentos_dir: Path = BACKEND_DIR / "armazenamento" / "documentos"
    documento_tamanho_maximo_mb: int = 10

    # OCR (Tesseract). Se o executável não existir, PDFs com texto continuam funcionando.
    tesseract_cmd: str = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    tessdata_dir: Path = BACKEND_DIR / "tessdata"
    ocr_idioma: str = "por"
    ocr_maximo_paginas: int = 10
    ocr_timeout_segundos: float = 60.0

    # Sessão de login
    sessao_duracao_horas: int = 12
    # Em produção com HTTPS deve ser True; localmente (HTTP) precisa ser False.
    cookie_seguro: bool = False

    # Ollama (IA local)
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:1b"
    ollama_timeout_seconds: float = 120.0
    # Tempo máximo para a checagem de status (deve ser curto).
    ollama_status_timeout_seconds: float = 3.0
    # Por quanto tempo o resultado do status fica em cache, evitando consultar o Ollama a cada requisição.
    ollama_status_cache_seconds: float = 10.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
