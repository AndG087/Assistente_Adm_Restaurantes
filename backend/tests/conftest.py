from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, make_url
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401  (registra as tabelas em Base.metadata)
from app.core.config import get_settings
from app.core.database import Base, get_db
from app.main import app
from app.services.ollama_service import StatusOllama, get_ollama_service


class FakeOllamaService:
    """Substitui o serviço real nos testes de rotas: nenhum teste depende do Ollama instalado."""

    def __init__(self) -> None:
        self.modelo = "modelo-teste:1b"
        self.status_atual = StatusOllama(ollama_disponivel=True, modelo=self.modelo, modelo_disponivel=True)
        self.resposta = "Olá! Como posso ajudar?"
        self.erro: Exception | None = None
        self.mensagens_recebidas: list[str] = []
        # Respostas de gerar_json, consumidas em ordem (a última se repete).
        self.respostas_json: list[dict] = [{}]
        self.pedidos_json: list[dict] = []

    async def status(self) -> StatusOllama:
        return self.status_atual

    async def conversar(self, mensagem: str) -> str:
        self.mensagens_recebidas.append(mensagem)
        if self.erro is not None:
            raise self.erro
        return self.resposta

    async def gerar_json(self, sistema: str, usuario: str, esquema: dict) -> dict:
        self.pedidos_json.append({"sistema": sistema, "usuario": usuario, "esquema": esquema})
        if self.erro is not None:
            raise self.erro
        return self.respostas_json.pop(0) if len(self.respostas_json) > 1 else self.respostas_json[0]


@pytest.fixture(scope="session")
def engine_teste() -> Iterator[Engine]:
    url = get_settings().test_database_url
    if not url:
        pytest.skip("TEST_DATABASE_URL não configurada em backend/.env")
    # Trava de segurança: estas tabelas são apagadas, então nunca rode contra o banco principal.
    if not (make_url(url).database or "").endswith("_test"):
        pytest.exit("TEST_DATABASE_URL deve apontar para um banco cujo nome termine em _test", returncode=1)

    engine = create_engine(url, pool_pre_ping=True)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db(engine_teste: Engine) -> Iterator[Session]:
    fabrica = sessionmaker(bind=engine_teste, autoflush=False, expire_on_commit=False)

    def get_db_teste() -> Iterator[Session]:
        sessao = fabrica()
        try:
            yield sessao
        finally:
            sessao.close()

    app.dependency_overrides[get_db] = get_db_teste
    sessao = fabrica()
    yield sessao
    sessao.close()
    # Cada teste começa com as tabelas vazias.
    with engine_teste.begin() as conexao:
        for tabela in reversed(Base.metadata.sorted_tables):
            conexao.execute(tabela.delete())


@pytest.fixture
def fake_ollama() -> FakeOllamaService:
    return FakeOllamaService()


@pytest.fixture
def novo_cliente(db: Session, fake_ollama: FakeOllamaService) -> Iterator[Callable[[], TestClient]]:
    """Fábrica de clientes HTTP independentes (cada um com seus próprios cookies)."""
    app.dependency_overrides[get_ollama_service] = lambda: fake_ollama
    clientes: list[TestClient] = []

    def criar() -> TestClient:
        cliente = TestClient(app)
        cliente.__enter__()
        clientes.append(cliente)
        return cliente

    yield criar
    for cliente in clientes:
        cliente.__exit__(None, None, None)
    app.dependency_overrides.clear()


@pytest.fixture
def client(novo_cliente: Callable[[], TestClient]) -> TestClient:
    """Cliente sem login."""
    return novo_cliente()


def registrar(cliente: TestClient, email: str = "ana@exemplo.com", nome: str = "Ana Souza") -> dict:
    resposta = cliente.post("/api/auth/registrar", json={"nome": nome, "email": email, "senha": "senha-segura-123"})
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


@pytest.fixture
def client_logado(novo_cliente: Callable[[], TestClient]) -> TestClient:
    cliente = novo_cliente()
    registrar(cliente)
    return cliente


def criar_restaurante(cliente: TestClient, nome: str = "Cantina da Ana") -> int:
    resposta = cliente.post("/api/restaurantes", json={"nome": nome})
    assert resposta.status_code == 201, resposta.text
    return resposta.json()["id"]


@pytest.fixture
def restaurante_id(client_logado: TestClient) -> int:
    """Restaurante do usuário de client_logado."""
    return criar_restaurante(client_logado)


@pytest.fixture
def intruso(novo_cliente: Callable[[], TestClient]) -> TestClient:
    """Outro usuário, com o próprio restaurante, para testar o isolamento."""
    cliente = novo_cliente()
    registrar(cliente, email="intruso@exemplo.com", nome="Intruso")
    criar_restaurante(cliente, "Restaurante do Intruso")
    return cliente
