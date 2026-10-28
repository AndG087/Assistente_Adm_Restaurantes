from app.services.categoria_service import CATEGORIAS_PADRAO


def url(restaurante_id: int, sufixo: str = "") -> str:
    return f"/api/restaurantes/{restaurante_id}/categorias{sufixo}"


def test_restaurante_novo_ja_tem_as_categorias_padrao(client_logado, restaurante_id):
    nomes = [c["nome"] for c in client_logado.get(url(restaurante_id)).json()]

    assert sorted(nomes) == sorted(CATEGORIAS_PADRAO)


def test_cria_categoria(client_logado, restaurante_id):
    resposta = client_logado.post(url(restaurante_id), json={"nome": "  Delivery   e apps "})

    assert resposta.status_code == 201
    assert resposta.json()["nome"] == "Delivery e apps"


def test_nome_repetido_ignora_maiusculas_e_acentos(client_logado, restaurante_id):
    assert client_logado.post(url(restaurante_id), json={"nome": "Bebidas"}).status_code == 409
    assert client_logado.post(url(restaurante_id), json={"nome": "GAS"}).status_code == 409


def test_renomeia_e_inativa(client_logado, restaurante_id):
    categoria = client_logado.post(url(restaurante_id), json={"nome": "Eventos"}).json()

    resposta = client_logado.put(url(restaurante_id, f"/{categoria['id']}"), json={"nome": "Festas", "ativo": False})

    assert resposta.status_code == 200
    assert resposta.json() == {"id": categoria["id"], "nome": "Festas", "ativo": False}
    ativas = [c["nome"] for c in client_logado.get(url(restaurante_id)).json()]
    todas = [c["nome"] for c in client_logado.get(url(restaurante_id), params={"incluir_inativas": True}).json()]
    assert "Festas" not in ativas
    assert "Festas" in todas


def test_renomear_para_nome_existente(client_logado, restaurante_id):
    categoria = client_logado.post(url(restaurante_id), json={"nome": "Eventos"}).json()

    resposta = client_logado.put(url(restaurante_id, f"/{categoria['id']}"), json={"nome": "Aluguel"})

    assert resposta.status_code == 409


def test_rejeita_nome_invalido(client_logado, restaurante_id):
    assert client_logado.post(url(restaurante_id), json={"nome": " "}).status_code == 422
    assert client_logado.post(url(restaurante_id), json={"nome": "x" * 61}).status_code == 422


def test_isolamento_entre_restaurantes(client_logado, restaurante_id, intruso):
    categoria_id = client_logado.get(url(restaurante_id)).json()[0]["id"]
    restaurante_do_intruso = intruso.get("/api/restaurantes").json()[0]["id"]

    assert intruso.get(url(restaurante_id)).status_code == 404
    resposta = intruso.put(url(restaurante_do_intruso, f"/{categoria_id}"), json={"nome": "Invadida"})
    assert resposta.status_code == 404
    assert all(c["nome"] != "Invadida" for c in client_logado.get(url(restaurante_id)).json())
