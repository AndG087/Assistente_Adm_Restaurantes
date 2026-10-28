import pytest

from tests.conftest import criar_restaurante


def url(restaurante_id: int, sufixo: str = "") -> str:
    return f"/api/restaurantes/{restaurante_id}/despesas{sufixo}"


def categoria_id(cliente, restaurante_id: int, nome: str) -> int:
    categorias = cliente.get(f"/api/restaurantes/{restaurante_id}/categorias").json()
    return next(c["id"] for c in categorias if c["nome"] == nome)


def criar_fornecedor(cliente, restaurante_id: int, nome: str = "Hortifruti Verde") -> int:
    return cliente.post(f"/api/restaurantes/{restaurante_id}/fornecedores", json={"nome": nome}).json()["id"]


def criar_despesa(cliente, restaurante_id: int, **campos) -> dict:
    corpo = {"descricao": "Compra de legumes", "valor": "150.00", "data": "2026-10-10"} | campos
    resposta = cliente.post(url(restaurante_id), json=corpo)
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


# --- criação e validação ---


def test_cria_despesa_completa(client_logado, restaurante_id):
    cat = categoria_id(client_logado, restaurante_id, "Alimentos e insumos")
    forn = criar_fornecedor(client_logado, restaurante_id)

    despesa = criar_despesa(
        client_logado,
        restaurante_id,
        descricao="  Legumes   da semana ",
        valor=1234.5,
        categoria_id=cat,
        fornecedor_id=forn,
        numero_documento="NF 4521",
        observacoes="",
    )

    assert despesa["descricao"] == "Legumes da semana"
    # Dinheiro sai como texto com 2 casas, sem arredondamentos de float.
    assert despesa["valor"] == "1234.50"
    assert despesa["data"] == "2026-10-10"
    assert despesa["categoria"] == {"id": cat, "nome": "Alimentos e insumos"}
    assert despesa["fornecedor"] == {"id": forn, "nome": "Hortifruti Verde"}
    assert despesa["numero_documento"] == "NF 4521"
    assert despesa["observacoes"] is None


def test_categoria_e_fornecedor_sao_opcionais(client_logado, restaurante_id):
    despesa = criar_despesa(client_logado, restaurante_id)

    assert despesa["categoria"] is None
    assert despesa["fornecedor"] is None


@pytest.mark.parametrize(
    "campos",
    [
        {"valor": "0"},
        {"valor": "-10"},
        {"valor": "10.555"},
        {"valor": "99999999999.00"},
        {"valor": "abc"},
        {"data": "2026-02-30"},
        {"data": "1999-12-31"},
        {"descricao": " "},
        {"descricao": "x" * 201},
        {"categoria_id": 0},
        {"restaurante_id": 1},
    ],
)
def test_rejeita_dados_invalidos(client_logado, restaurante_id, campos):
    corpo = {"descricao": "Compra", "valor": "10.00", "data": "2026-10-10"} | campos
    assert client_logado.post(url(restaurante_id), json=corpo).status_code == 422


def test_soma_de_centavos_e_exata(client_logado, restaurante_id):
    # Com float, 0.1 + 0.2 daria 0.30000000000000004.
    criar_despesa(client_logado, restaurante_id, valor="0.10")
    criar_despesa(client_logado, restaurante_id, valor="0.20")

    assert client_logado.get(url(restaurante_id)).json()["valor_total"] == "0.30"


# --- isolamento de referências ---


def test_nao_aceita_categoria_ou_fornecedor_de_outro_restaurante(client_logado, restaurante_id):
    outro = criar_restaurante(client_logado, "Outro restaurante")
    cat_de_outro = categoria_id(client_logado, outro, "Bebidas")
    forn_de_outro = criar_fornecedor(client_logado, outro)

    r1 = client_logado.post(
        url(restaurante_id), json={"descricao": "Compra", "valor": "1", "data": "2026-10-10", "categoria_id": cat_de_outro}
    )
    r2 = client_logado.post(
        url(restaurante_id),
        json={"descricao": "Compra", "valor": "1", "data": "2026-10-10", "fornecedor_id": forn_de_outro},
    )

    assert r1.status_code == 422
    assert r1.json()["detail"] == "Categoria não encontrada."
    assert r2.status_code == 422
    assert r2.json()["detail"] == "Fornecedor não encontrado."


def test_inativos_nao_podem_ser_escolhidos_mas_continuam_em_despesas_antigas(client_logado, restaurante_id):
    forn = criar_fornecedor(client_logado, restaurante_id)
    despesa = criar_despesa(client_logado, restaurante_id, fornecedor_id=forn)
    client_logado.put(
        f"/api/restaurantes/{restaurante_id}/fornecedores/{forn}", json={"nome": "Hortifruti Verde", "ativo": False}
    )

    nova = client_logado.post(
        url(restaurante_id), json={"descricao": "Nova", "valor": "5", "data": "2026-10-11", "fornecedor_id": forn}
    )
    assert nova.status_code == 422
    assert nova.json()["detail"] == "O fornecedor selecionado está inativo."

    # Editar a despesa antiga mantendo o fornecedor inativo é permitido.
    edicao = client_logado.put(
        url(restaurante_id, f"/{despesa['id']}"),
        json={"descricao": "Editada", "valor": "151", "data": "2026-10-10", "fornecedor_id": forn},
    )
    assert edicao.status_code == 200
    assert edicao.json()["fornecedor"]["nome"] == "Hortifruti Verde"


# --- listagem, filtros e totais ---


@pytest.fixture
def varias_despesas(client_logado, restaurante_id):
    bebidas = categoria_id(client_logado, restaurante_id, "Bebidas")
    aluguel = categoria_id(client_logado, restaurante_id, "Aluguel")
    forn = criar_fornecedor(client_logado, restaurante_id, "Distribuidora Sul")
    criar_despesa(client_logado, restaurante_id, descricao="Refrigerantes", valor="300.00", data="2026-09-05",
                  categoria_id=bebidas, fornecedor_id=forn)
    criar_despesa(client_logado, restaurante_id, descricao="Aluguel setembro", valor="2500.00", data="2026-09-10",
                  categoria_id=aluguel)
    criar_despesa(client_logado, restaurante_id, descricao="Cervejas", valor="450.50", data="2026-10-02",
                  categoria_id=bebidas, numero_documento="NF 100")
    criar_despesa(client_logado, restaurante_id, descricao="Conserto da pia", valor="120.00", data="2026-10-15")
    return {"bebidas": bebidas, "aluguel": aluguel, "fornecedor": forn}


def descricoes(cliente, restaurante_id, **params):
    return [d["descricao"] for d in cliente.get(url(restaurante_id), params=params).json()["itens"]]


def test_lista_da_mais_recente_para_a_mais_antiga(client_logado, restaurante_id, varias_despesas):
    corpo = client_logado.get(url(restaurante_id)).json()

    assert [d["descricao"] for d in corpo["itens"]] == [
        "Conserto da pia", "Cervejas", "Aluguel setembro", "Refrigerantes"
    ]
    assert corpo["total"] == 4
    assert corpo["valor_total"] == "3370.50"


def test_filtros(client_logado, restaurante_id, varias_despesas):
    rid = restaurante_id
    assert descricoes(client_logado, rid, de="2026-09-01", ate="2026-09-30") == ["Aluguel setembro", "Refrigerantes"]
    assert descricoes(client_logado, rid, categoria_id=varias_despesas["bebidas"]) == ["Cervejas", "Refrigerantes"]
    assert descricoes(client_logado, rid, sem_categoria=True) == ["Conserto da pia"]
    assert descricoes(client_logado, rid, fornecedor_id=varias_despesas["fornecedor"]) == ["Refrigerantes"]
    assert descricoes(client_logado, rid, busca="cerv") == ["Cervejas"]
    assert descricoes(client_logado, rid, busca="NF 100") == ["Cervejas"]


def test_totais_consideram_todos_os_filtrados_e_nao_so_a_pagina(client_logado, restaurante_id, varias_despesas):
    pagina = client_logado.get(url(restaurante_id), params={"limite": 2, "deslocamento": 1}).json()

    assert [d["descricao"] for d in pagina["itens"]] == ["Cervejas", "Aluguel setembro"]
    assert pagina["total"] == 4
    assert pagina["valor_total"] == "3370.50"


def test_periodo_invertido(client_logado, restaurante_id):
    resposta = client_logado.get(url(restaurante_id), params={"de": "2026-10-31", "ate": "2026-10-01"})
    assert resposta.status_code == 422


def test_resumo_por_categoria(client_logado, restaurante_id, varias_despesas):
    resumo = client_logado.get(url(restaurante_id, "/resumo"), params={"de": "2026-09-01", "ate": "2026-10-31"}).json()

    assert resumo["quantidade"] == 4
    assert resumo["valor_total"] == "3370.50"
    assert [(c["categoria"]["nome"] if c["categoria"] else None, c["quantidade"], c["valor_total"])
            for c in resumo["por_categoria"]] == [
        ("Aluguel", 1, "2500.00"),
        ("Bebidas", 2, "750.50"),
        (None, 1, "120.00"),
    ]


def test_resumo_sem_despesas(client_logado, restaurante_id):
    assert client_logado.get(url(restaurante_id, "/resumo")).json() == {
        "quantidade": 0, "valor_total": "0.00", "por_categoria": []
    }


# --- edição e exclusão ---


def test_edita_e_exclui(client_logado, restaurante_id):
    despesa = criar_despesa(client_logado, restaurante_id)

    editada = client_logado.put(
        url(restaurante_id, f"/{despesa['id']}"), json={"descricao": "Legumes", "valor": "99.90", "data": "2026-10-12"}
    )
    assert editada.status_code == 200
    assert editada.json()["valor"] == "99.90"

    assert client_logado.delete(url(restaurante_id, f"/{despesa['id']}")).status_code == 204
    assert client_logado.get(url(restaurante_id, f"/{despesa['id']}")).status_code == 404


def test_isolamento_entre_restaurantes(client_logado, restaurante_id, intruso):
    despesa = criar_despesa(client_logado, restaurante_id)
    rid_intruso = intruso.get("/api/restaurantes").json()[0]["id"]

    assert intruso.get(url(restaurante_id)).status_code == 404
    assert intruso.get(url(rid_intruso, f"/{despesa['id']}")).status_code == 404
    assert intruso.delete(url(rid_intruso, f"/{despesa['id']}")).status_code == 404
    assert intruso.get(url(rid_intruso)).json()["total"] == 0
    assert intruso.get(url(rid_intruso, "/resumo")).json()["quantidade"] == 0

    assert client_logado.get(url(restaurante_id, f"/{despesa['id']}")).status_code == 200
