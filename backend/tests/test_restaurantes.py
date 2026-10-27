import pytest

from app.schemas.restaurante import cnpj_valido
from tests.conftest import registrar

CNPJ_VALIDO = "11.222.333/0001-81"


def test_cria_restaurante_e_usuario_vira_proprietario(client_logado):
    resposta = client_logado.post("/api/restaurantes", json={"nome": " Cantina   da Ana ", "cnpj": CNPJ_VALIDO})

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["nome"] == "Cantina da Ana"
    assert corpo["cnpj"] == "11222333000181"
    assert corpo["papel"] == "proprietario"


def test_cnpj_e_opcional(client_logado):
    resposta = client_logado.post("/api/restaurantes", json={"nome": "Bar do Zé", "cnpj": ""})

    assert resposta.status_code == 201
    assert resposta.json()["cnpj"] is None


@pytest.mark.parametrize(
    "corpo",
    [
        {"nome": "Bar", "cnpj": "11.222.333/0001-82"},
        {"nome": "Bar", "cnpj": "123"},
        {"nome": " "},
        {},
        {"nome": "Bar", "id": 99},
    ],
)
def test_rejeita_restaurante_invalido(client_logado, corpo):
    assert client_logado.post("/api/restaurantes", json=corpo).status_code == 422


def test_rotas_de_restaurante_exigem_login(client):
    assert client.get("/api/restaurantes").status_code == 401
    assert client.post("/api/restaurantes", json={"nome": "Bar"}).status_code == 401
    assert client.get("/api/restaurantes/1").status_code == 401


def test_lista_apenas_os_restaurantes_do_usuario(novo_cliente):
    ana = novo_cliente()
    registrar(ana, email="ana@exemplo.com")
    bruno = novo_cliente()
    registrar(bruno, email="bruno@exemplo.com")

    ana.post("/api/restaurantes", json={"nome": "Cantina da Ana"})
    ana.post("/api/restaurantes", json={"nome": "Ana Lanches"})
    bruno.post("/api/restaurantes", json={"nome": "Bar do Bruno"})

    assert [r["nome"] for r in ana.get("/api/restaurantes").json()] == ["Ana Lanches", "Cantina da Ana"]
    assert [r["nome"] for r in bruno.get("/api/restaurantes").json()] == ["Bar do Bruno"]


def test_usuario_nao_acessa_restaurante_de_outro(novo_cliente):
    ana = novo_cliente()
    registrar(ana, email="ana@exemplo.com")
    bruno = novo_cliente()
    registrar(bruno, email="bruno@exemplo.com")
    id_da_ana = ana.post("/api/restaurantes", json={"nome": "Cantina da Ana"}).json()["id"]

    assert ana.get(f"/api/restaurantes/{id_da_ana}").status_code == 200

    # 404 igual ao de um id inexistente: não revela que o restaurante existe.
    proibido = bruno.get(f"/api/restaurantes/{id_da_ana}")
    inexistente = bruno.get("/api/restaurantes/999999")
    assert proibido.status_code == inexistente.status_code == 404
    assert proibido.json() == inexistente.json()


@pytest.mark.parametrize("restaurante_id", ["0", "-1", "abc"])
def test_id_de_restaurante_invalido(client_logado, restaurante_id):
    assert client_logado.get(f"/api/restaurantes/{restaurante_id}").status_code == 422


@pytest.mark.parametrize(
    ("cnpj", "valido"),
    [
        ("11222333000181", True),
        ("11444777000161", True),
        ("11222333000182", False),
        ("00000000000000", False),
        ("1122233300018", False),
    ],
)
def test_digitos_verificadores_do_cnpj(cnpj, valido):
    assert cnpj_valido(cnpj) is valido
