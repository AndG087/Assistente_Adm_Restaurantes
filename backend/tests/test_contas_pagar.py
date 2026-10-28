from datetime import date

import pytest

from app.core import tempo

HOJE = date(2026, 10, 20)


@pytest.fixture(autouse=True)
def hoje_fixo(monkeypatch):
    monkeypatch.setattr(tempo, "hoje", lambda: HOJE)


def url(restaurante_id: int, sufixo: str = "") -> str:
    return f"/api/restaurantes/{restaurante_id}/contas-a-pagar{sufixo}"


def criar_conta(cliente, restaurante_id: int, **campos) -> dict:
    corpo = {"descricao": "Boleto do gás", "valor": "380.00", "data_vencimento": "2026-10-25"} | campos
    resposta = cliente.post(url(restaurante_id), json=corpo)
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def categoria_id(cliente, restaurante_id: int, nome: str) -> int:
    categorias = cliente.get(f"/api/restaurantes/{restaurante_id}/categorias").json()
    return next(c["id"] for c in categorias if c["nome"] == nome)


# --- criação e situação ---


@pytest.mark.parametrize(
    ("vencimento", "situacao"),
    [("2026-10-19", "vencida"), ("2026-10-20", "vence_hoje"), ("2026-10-21", "a_vencer")],
)
def test_situacao_depende_do_vencimento(client_logado, restaurante_id, vencimento, situacao):
    conta = criar_conta(client_logado, restaurante_id, data_vencimento=vencimento)

    assert conta["situacao"] == situacao
    assert conta["data_pagamento"] is None
    assert conta["despesa_id"] is None


def test_cria_conta_completa(client_logado, restaurante_id):
    gas = categoria_id(client_logado, restaurante_id, "Gás")
    fornecedor = client_logado.post(
        f"/api/restaurantes/{restaurante_id}/fornecedores", json={"nome": "Gás Express"}
    ).json()["id"]

    conta = criar_conta(
        client_logado, restaurante_id, categoria_id=gas, fornecedor_id=fornecedor, numero_documento="Boleto 123"
    )

    assert conta["valor"] == "380.00"
    assert conta["categoria"] == {"id": gas, "nome": "Gás"}
    assert conta["fornecedor"] == {"id": fornecedor, "nome": "Gás Express"}


@pytest.mark.parametrize(
    "campos",
    [{"valor": "0"}, {"valor": "1.001"}, {"data_vencimento": "2026-13-01"}, {"data_vencimento": None}, {"x": 1}],
)
def test_rejeita_dados_invalidos(client_logado, restaurante_id, campos):
    corpo = {"descricao": "Conta", "valor": "10", "data_vencimento": "2026-10-25"} | campos
    assert client_logado.post(url(restaurante_id), json=corpo).status_code == 422


# --- pagamento ---


def test_pagar_gera_a_despesa(client_logado, restaurante_id):
    gas = categoria_id(client_logado, restaurante_id, "Gás")
    conta = criar_conta(client_logado, restaurante_id, categoria_id=gas, numero_documento="Boleto 123")

    paga = client_logado.post(url(restaurante_id, f"/{conta['id']}/pagar"), json={"data_pagamento": "2026-10-18"})

    assert paga.status_code == 200
    corpo = paga.json()
    assert corpo["situacao"] == "paga"
    assert corpo["data_pagamento"] == "2026-10-18"

    despesa = client_logado.get(f"/api/restaurantes/{restaurante_id}/despesas/{corpo['despesa_id']}").json()
    assert despesa["descricao"] == "Boleto do gás"
    assert despesa["valor"] == "380.00"
    # A despesa entra na data em que o dinheiro saiu.
    assert despesa["data"] == "2026-10-18"
    assert despesa["categoria"]["nome"] == "Gás"
    assert despesa["numero_documento"] == "Boleto 123"
    assert despesa["conta_pagar_id"] == conta["id"]


def test_pagar_sem_data_usa_hoje(client_logado, restaurante_id):
    conta = criar_conta(client_logado, restaurante_id)

    assert client_logado.post(url(restaurante_id, f"/{conta['id']}/pagar")).json()["data_pagamento"] == "2026-10-20"


def test_nao_paga_com_data_futura_nem_duas_vezes(client_logado, restaurante_id):
    conta = criar_conta(client_logado, restaurante_id)
    pagar = url(restaurante_id, f"/{conta['id']}/pagar")

    assert client_logado.post(pagar, json={"data_pagamento": "2026-10-21"}).status_code == 409
    assert client_logado.post(pagar).status_code == 200
    assert client_logado.post(pagar).status_code == 409


def test_conta_paga_nao_pode_ser_alterada_nem_excluida(client_logado, restaurante_id):
    conta = criar_conta(client_logado, restaurante_id)
    client_logado.post(url(restaurante_id, f"/{conta['id']}/pagar"))

    edicao = client_logado.put(
        url(restaurante_id, f"/{conta['id']}"),
        json={"descricao": "Outra", "valor": "1", "data_vencimento": "2026-10-25"},
    )
    assert edicao.status_code == 409
    assert client_logado.delete(url(restaurante_id, f"/{conta['id']}")).status_code == 409


def test_despesa_gerada_so_muda_pela_conta(client_logado, restaurante_id):
    conta = criar_conta(client_logado, restaurante_id)
    despesa_id = client_logado.post(url(restaurante_id, f"/{conta['id']}/pagar")).json()["despesa_id"]
    url_despesa = f"/api/restaurantes/{restaurante_id}/despesas/{despesa_id}"

    assert client_logado.delete(url_despesa).status_code == 409
    edicao = client_logado.put(url_despesa, json={"descricao": "Outra", "valor": "1", "data": "2026-10-20"})
    assert edicao.status_code == 409


def test_desfazer_pagamento_remove_a_despesa(client_logado, restaurante_id):
    conta = criar_conta(client_logado, restaurante_id)
    despesa_id = client_logado.post(url(restaurante_id, f"/{conta['id']}/pagar")).json()["despesa_id"]

    resposta = client_logado.post(url(restaurante_id, f"/{conta['id']}/desfazer-pagamento"))

    assert resposta.status_code == 200
    assert resposta.json()["situacao"] == "a_vencer"
    assert resposta.json()["despesa_id"] is None
    assert client_logado.get(f"/api/restaurantes/{restaurante_id}/despesas/{despesa_id}").status_code == 404
    # Desfazer de novo não faz sentido.
    assert client_logado.post(url(restaurante_id, f"/{conta['id']}/desfazer-pagamento")).status_code == 409


def test_edita_e_exclui_conta_pendente(client_logado, restaurante_id):
    conta = criar_conta(client_logado, restaurante_id)

    edicao = client_logado.put(
        url(restaurante_id, f"/{conta['id']}"),
        json={"descricao": "Boleto do gás (outubro)", "valor": "390.10", "data_vencimento": "2026-10-19"},
    )
    assert edicao.status_code == 200
    assert edicao.json()["situacao"] == "vencida"
    assert edicao.json()["valor"] == "390.10"

    assert client_logado.delete(url(restaurante_id, f"/{conta['id']}")).status_code == 204
    assert client_logado.get(url(restaurante_id, f"/{conta['id']}")).status_code == 404


# --- listagem e alertas ---


@pytest.fixture
def varias_contas(client_logado, restaurante_id):
    contas = {
        "aluguel": criar_conta(client_logado, restaurante_id, descricao="Aluguel", valor="3000",
                               data_vencimento="2026-10-10"),
        "energia": criar_conta(client_logado, restaurante_id, descricao="Energia", valor="800.40",
                               data_vencimento="2026-10-20"),
        "agua": criar_conta(client_logado, restaurante_id, descricao="Água", valor="210",
                            data_vencimento="2026-10-24"),
        "internet": criar_conta(client_logado, restaurante_id, descricao="Internet", valor="150",
                                data_vencimento="2026-11-15"),
        "gas": criar_conta(client_logado, restaurante_id, descricao="Gás", valor="380",
                           data_vencimento="2026-10-05"),
    }
    client_logado.post(url(restaurante_id, f"/{contas['gas']['id']}/pagar"), json={"data_pagamento": "2026-10-05"})
    return contas


def descricoes(cliente, restaurante_id, **params):
    return [c["descricao"] for c in cliente.get(url(restaurante_id), params=params).json()["itens"]]


def test_lista_pendentes_por_vencimento(client_logado, restaurante_id, varias_contas):
    corpo = client_logado.get(url(restaurante_id)).json()

    assert [c["descricao"] for c in corpo["itens"]] == ["Aluguel", "Energia", "Água", "Internet"]
    assert [c["situacao"] for c in corpo["itens"]] == ["vencida", "vence_hoje", "a_vencer", "a_vencer"]
    assert corpo["total"] == 4
    assert corpo["valor_total"] == "4160.40"


def test_filtros_de_situacao_e_periodo(client_logado, restaurante_id, varias_contas):
    rid = restaurante_id
    assert descricoes(client_logado, rid, situacao="vencidas") == ["Aluguel"]
    assert descricoes(client_logado, rid, situacao="pagas") == ["Gás"]
    assert len(descricoes(client_logado, rid, situacao="todas")) == 5
    assert descricoes(client_logado, rid, de="2026-10-15", ate="2026-10-31") == ["Energia", "Água"]
    assert descricoes(client_logado, rid, busca="internet") == ["Internet"]
    assert client_logado.get(url(rid), params={"situacao": "invalida"}).status_code == 422


def test_alertas_de_vencimento(client_logado, restaurante_id, varias_contas):
    alertas = client_logado.get(url(restaurante_id, "/alertas")).json()

    assert alertas == {
        "hoje": "2026-10-20",
        "dias": 7,
        "vencidas": {"quantidade": 1, "valor_total": "3000.00"},
        "vencem_hoje": {"quantidade": 1, "valor_total": "800.40"},
        # Água (24/10) entra; Internet (15/11) fica fora dos 7 dias; o gás já foi pago.
        "proximos_dias": {"quantidade": 1, "valor_total": "210.00"},
    }

    com_30_dias = client_logado.get(url(restaurante_id, "/alertas"), params={"dias": 30}).json()
    assert com_30_dias["proximos_dias"]["quantidade"] == 2


def test_alertas_sem_contas(client_logado, restaurante_id):
    alertas = client_logado.get(url(restaurante_id, "/alertas")).json()

    assert alertas["vencidas"] == {"quantidade": 0, "valor_total": "0.00"}


# --- isolamento ---


def test_isolamento_entre_restaurantes(client_logado, restaurante_id, intruso):
    conta = criar_conta(client_logado, restaurante_id)
    rid_intruso = intruso.get("/api/restaurantes").json()[0]["id"]

    assert intruso.get(url(restaurante_id)).status_code == 404
    assert intruso.get(url(restaurante_id, "/alertas")).status_code == 404
    assert intruso.get(url(rid_intruso, f"/{conta['id']}")).status_code == 404
    assert intruso.post(url(rid_intruso, f"/{conta['id']}/pagar")).status_code == 404
    assert intruso.delete(url(rid_intruso, f"/{conta['id']}")).status_code == 404
    assert intruso.get(url(rid_intruso, "/alertas")).json()["proximos_dias"]["quantidade"] == 0

    assert client_logado.get(url(restaurante_id, f"/{conta['id']}")).json()["situacao"] == "a_vencer"
