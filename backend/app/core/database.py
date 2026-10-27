"""Conexão com o banco de dados via SQLAlchemy."""

from collections.abc import Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

_settings = get_settings()

# connect_timeout evita que a checagem de saúde fique travada se o MySQL estiver parado.
_connect_args = {"connect_timeout": 3} if _settings.database_url.startswith("mysql") else {}

# A conexão só é aberta quando usada, então importar este módulo não exige o MySQL ligado.
engine = create_engine(_settings.database_url, pool_pre_ping=True, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """Classe base de todos os modelos de persistência."""


def get_db() -> Iterator[Session]:
    """Dependência do FastAPI: abre uma sessão por requisição e garante o fechamento."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verificar_conexao() -> bool:
    """Retorna True se o banco responde a uma consulta simples."""
    try:
        with engine.connect() as conexao:
            conexao.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError:
        return False
