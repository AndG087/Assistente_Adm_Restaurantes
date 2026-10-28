import pytest

from tests.conftest import criar_restaurante


def url(restaurante_id: int, sufixo: str = "") -> str:
    return f"/api/restaurantes/{restaurante_id}/fornecedores{sufixo}"


FORNECEDOR = {
    "nome": "  Distribuidora   Boa Comida ",
    "documento": "11.222.333/0001-81",
    "telefone": "(11) 98765-4321",
    "email": "Vendas@BoaComida.com.br",
    "observacoes": "Entrega às terças",
}


def test_cria_e_obtem_fornecedor(client_logado, restaurante_id):
    resposta = client_logado.post(url(restaurante_id), json=FORNECEDOR)

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["nome"] == "Distribuidora Boa Comida"
    assert corpo["documento"] == "11222333000181"
    assert corpo["email"] == "vendas@boacomida.com.br"
    assert corpo["ativo"] is True
    assert client_logado.get(url(restaurante_id, f"/{corpo['id']}")).json() == corpo


def test_apenas_nome_e_obrigatorio(client_logado, restaurante_id):
    resposta = client_logado.post(url(restaurante_id), json={"nome": "Feira do Zé", "documento": ""})

    assert resposta.status_code == 201
    assert resposta.json()["documento"] is None


@pytest.mark.parametrize(
    "corpo",
    [
        {"nome": "X"},
        {"nome": "Fornecedor", "documento": "123"},
        {"nome": "Fornecedor", "documento": "11.222.333/0001-82"},
        {"nome": "Fornecedor", "email": "invalido"},
        {"nome": "Fornecedor", "telefone": "abc"},
        {"nome": "Fornecedor", "observacoes": "x" * 501},
        {"nome": "Fornecedor", "restaurante_id": 99},
    ],
)
def test_rejeita_dados_invalidos(client_logado, restaurante_id, corpo):
    assert client_logado.post(url(restaurante_id), json=corpo).status_code == 422


def test_documento_repetido_no_mesmo_restaurante(client_logado, restaurante_id):
    client_logado.post(url(restaurante_id), json={"nome": "Fornecedor A", "documento": "52998224725"})

    resposta = client_logado.post(url(restaurante_id), json={"nome": "Fornecedor B", "documento": "529.982.247-25"})

    assert resposta.status_code == 409


def test_mesmo_documento_em_restaurantes_diferentes(client_logado, restaurante_id):
    outro = criar_restaurante(client_logado, "Segundo restaurante")
    corpo = {"nome": "Fornecedor", "documento": "52998224725"}

    assert client_logado.post(url(restaurante_id), json=corpo).status_code == 201
    assert client_logado.post(url(outro), json=corpo).status_code == 201


def test_lista_em_ordem_com_busca_e_inativos(client_logado, restaurante_id):
    ids = {}
    for nome, documento in [("Hortifruti Verde", None), ("Açougue Central", "52998224725"), ("Bebidas Sul", None)]:
        ids[nome] = client_logado.post(url(restaurante_id), json={"nome": nome, "documento": documento}).json()["id"]
    client_logado.put(url(restaurante_id, f"/{ids['Bebidas Sul']}"), json={"nome": "Bebidas Sul", "ativo": False})

    def nomes(**params):
        return [f["nome"] for f in client_logado.get(url(restaurante_id), params=params).json()]

    assert nomes() == ["Açougue Central", "Hortifruti Verde"]
    assert nomes(incluir_inativos=True) == ["Açougue Central", "Bebidas Sul", "Hortifruti Verde"]
    assert nomes(busca="verde") == ["Hortifruti Verde"]
    assert nomes(busca="529.982") == ["Açougue Central"]
    # Caracteres curinga do SQL são tratados como texto.
    assert nomes(busca="%") == []


def test_atualiza_fornecedor(client_logado, restaurante_id):
    fornecedor_id = client_logado.post(url(restaurante_id), json=FORNECEDOR).json()["id"]

    resposta = client_logado.put(url(restaurante_id, f"/{fornecedor_id}"), json={"nome": "Novo nome", "ativo": False})

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["nome"] == "Novo nome"
    assert corpo["ativo"] is False
    # PUT substitui tudo: campos omitidos ficam vazios.
    assert corpo["documento"] is None


def test_isolamento_entre_restaurantes(client_logado, restaurante_id, intruso):
    fornecedor_id = client_logado.post(url(restaurante_id), json=FORNECEDOR).json()["id"]
    restaurante_do_intruso = intruso.get("/api/restaurantes").json()[0]["id"]

    # O intruso não acessa o restaurante alheio...
    assert intruso.get(url(restaurante_id)).status_code == 404
    assert intruso.post(url(restaurante_id), json={"nome": "Invasor"}).status_code == 404
    # ...nem alcança o fornecedor pelo próprio restaurante.
    assert intruso.get(url(restaurante_do_intruso, f"/{fornecedor_id}")).status_code == 404
    resposta = intruso.put(url(restaurante_do_intruso, f"/{fornecedor_id}"), json={"nome": "Alterado"})
    assert resposta.status_code == 404
    assert intruso.get(url(restaurante_do_intruso)).json() == []

    assert client_logado.get(url(restaurante_id, f"/{fornecedor_id}")).json()["nome"] == "Distribuidora Boa Comida"


def test_exige_login(client):
    assert client.get(url(1)).status_code == 401
