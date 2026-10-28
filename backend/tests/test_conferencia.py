import pytest

from app.core.config import get_settings
from tests.arquivos import NOTA, pdf_com_texto

CHAVE = "35261011222333000181550010000045211000000123"


@pytest.fixture(autouse=True)
def pasta_temporaria(monkeypatch, tmp_path):
    monkeypatch.setattr(get_settings(), "documentos_dir", tmp_path)


def base(restaurante_id: int) -> str:
    return f"/api/restaurantes/{restaurante_id}"


def enviar(cliente, restaurante_id, linhas, nome="nota.pdf") -> dict:
    resposta = cliente.post(
        f"{base(restaurante_id)}/documentos", files={"arquivo": (nome, pdf_com_texto(linhas), "application/pdf")}
    )
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def confirmar(cliente, restaurante_id, documento_id, **campos):
    corpo = {"tipo": "despesa", "descricao": "Compra NF 4521", "valor": "1234.56", "data": "2026-10-05"} | campos
    return cliente.post(f"{base(restaurante_id)}/documentos/{documento_id}/confirmar", json=corpo)


def conferencia(cliente, restaurante_id, documento_id) -> dict:
    return cliente.get(f"{base(restaurante_id)}/documentos/{documento_id}/conferencia").json()


# --- sugestões ---


def test_reconhece_fornecedor_cadastrado_pelo_cnpj(client_logado, restaurante_id):
    fornecedor = client_logado.post(
        f"{base(restaurante_id)}/fornecedores", json={"nome": "Boa Comida", "documento": "11.222.333/0001-81"}
    ).json()
    doc = enviar(client_logado, restaurante_id, NOTA)

    assert conferencia(client_logado, restaurante_id, doc["id"])["fornecedor_sugerido"] == {
        "id": fornecedor["id"],
        "nome": "Boa Comida",
    }


def test_sem_fornecedor_cadastrado_nao_sugere(client_logado, restaurante_id):
    doc = enviar(client_logado, restaurante_id, NOTA)

    assert conferencia(client_logado, restaurante_id, doc["id"]) == {
        "fornecedor_sugerido": None,
        "possiveis_duplicados": [],
    }


# --- confirmação ---


def test_confirmar_como_despesa(client_logado, restaurante_id):
    doc = enviar(client_logado, restaurante_id, NOTA)

    resposta = confirmar(client_logado, restaurante_id, doc["id"], numero_documento="4521")

    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert corpo["status"] == "concluido"
    despesa = client_logado.get(f"{base(restaurante_id)}/despesas/{corpo['despesa_id']}").json()
    assert despesa["valor"] == "1234.56"
    assert despesa["numero_documento"] == "4521"


def test_confirmar_como_conta_a_pagar(client_logado, restaurante_id):
    doc = enviar(client_logado, restaurante_id, ["Boleto", "Vencimento 25/10/2026", "Valor do documento 380,00"])

    corpo = confirmar(
        client_logado, restaurante_id, doc["id"], tipo="conta", descricao="Boleto do gás", valor="380.00",
        data="2026-10-25",
    ).json()

    conta = client_logado.get(f"{base(restaurante_id)}/contas-a-pagar/{corpo['conta_pagar_id']}").json()
    assert conta["data_vencimento"] == "2026-10-25"
    assert conta["situacao"] in {"a_vencer", "vence_hoje", "vencida"}


def test_confirmar_valida_os_dados_e_o_restaurante(client_logado, restaurante_id, intruso):
    doc = enviar(client_logado, restaurante_id, NOTA)
    rid_intruso = intruso.get("/api/restaurantes").json()[0]["id"]
    forn_intruso = intruso.post(f"{base(rid_intruso)}/fornecedores", json={"nome": "Alheio"}).json()["id"]

    assert confirmar(client_logado, restaurante_id, doc["id"], valor="0").status_code == 422
    assert confirmar(client_logado, restaurante_id, doc["id"], tipo="outro").status_code == 422
    resposta = confirmar(client_logado, restaurante_id, doc["id"], fornecedor_id=forn_intruso)
    assert resposta.status_code == 422
    assert resposta.json()["detail"] == "Fornecedor não encontrado."
    # Nada foi criado e o documento continua pendente.
    assert client_logado.get(f"{base(restaurante_id)}/despesas").json()["total"] == 0
    assert client_logado.get(f"{base(restaurante_id)}/documentos/{doc['id']}").json()["status"] == "pendente"


def test_nao_confirma_duas_vezes_e_documento_conferido_nao_e_apagado(client_logado, restaurante_id):
    doc = enviar(client_logado, restaurante_id, NOTA)
    confirmar(client_logado, restaurante_id, doc["id"])

    assert confirmar(client_logado, restaurante_id, doc["id"]).status_code == 409
    assert client_logado.post(f"{base(restaurante_id)}/documentos/{doc['id']}/descartar").status_code == 409
    assert client_logado.delete(f"{base(restaurante_id)}/documentos/{doc['id']}").status_code == 409


def test_descartar(client_logado, restaurante_id):
    doc = enviar(client_logado, restaurante_id, NOTA)

    resposta = client_logado.post(f"{base(restaurante_id)}/documentos/{doc['id']}/descartar")

    assert resposta.json()["status"] == "descartado"
    assert confirmar(client_logado, restaurante_id, doc["id"]).status_code == 409


# --- possíveis duplicados ---


def test_mesma_chave_de_acesso_em_outro_documento(client_logado, restaurante_id):
    primeiro = enviar(client_logado, restaurante_id, [*NOTA, f"CHAVE DE ACESSO {CHAVE}"])
    # Mesmo conteúdo relevante, arquivo diferente (ex.: foto e PDF da mesma nota).
    segundo = enviar(client_logado, restaurante_id, [f"CHAVE {CHAVE}", "Total 1.234,56"], "foto.pdf")

    duplicados = conferencia(client_logado, restaurante_id, segundo["id"])["possiveis_duplicados"]

    assert [(d["tipo"], d["id"], d["motivo"]) for d in duplicados] == [
        ("documento", primeiro["id"], "Mesma chave de acesso da NF-e")
    ]


def test_mesmo_valor_em_data_proxima(client_logado, restaurante_id):
    despesa = client_logado.post(
        f"{base(restaurante_id)}/despesas", json={"descricao": "Compra já lançada", "valor": "1234.56", "data": "2026-10-07"}
    ).json()
    longe = client_logado.post(
        f"{base(restaurante_id)}/despesas", json={"descricao": "Outra", "valor": "1234.56", "data": "2026-10-20"}
    ).json()
    doc = enviar(client_logado, restaurante_id, NOTA)  # emissão 05/10, valor 1.234,56

    duplicados = conferencia(client_logado, restaurante_id, doc["id"])["possiveis_duplicados"]

    assert [(d["tipo"], d["id"]) for d in duplicados] == [("despesa", despesa["id"])]
    assert duplicados[0]["motivo"] == "Mesmo valor em data próxima"
    assert longe["id"] not in [d["id"] for d in duplicados]


def test_mesmo_numero_e_fornecedor(client_logado, restaurante_id):
    fornecedor = client_logado.post(
        f"{base(restaurante_id)}/fornecedores", json={"nome": "Boa Comida", "documento": "11222333000181"}
    ).json()["id"]
    conta = client_logado.post(
        f"{base(restaurante_id)}/contas-a-pagar",
        json={"descricao": "NF 4521", "valor": "999.00", "data_vencimento": "2026-12-01",
              "fornecedor_id": fornecedor, "numero_documento": "NF 4521"},
    ).json()
    doc = enviar(client_logado, restaurante_id, NOTA)

    duplicados = conferencia(client_logado, restaurante_id, doc["id"])["possiveis_duplicados"]

    assert [(d["tipo"], d["id"], d["motivo"]) for d in duplicados] == [
        ("conta", conta["id"], "Mesmo número de documento e fornecedor")
    ]


def test_conta_paga_aparece_uma_vez_so(client_logado, restaurante_id):
    conta = client_logado.post(
        f"{base(restaurante_id)}/contas-a-pagar",
        json={"descricao": "Compra", "valor": "1234.56", "data_vencimento": "2026-10-05"},
    ).json()
    client_logado.post(
        f"{base(restaurante_id)}/contas-a-pagar/{conta['id']}/pagar", json={"data_pagamento": "2026-10-05"}
    )
    doc = enviar(client_logado, restaurante_id, NOTA)

    duplicados = conferencia(client_logado, restaurante_id, doc["id"])["possiveis_duplicados"]

    # A despesa gerada pelo pagamento é a mesma operação da conta: só a conta é listada.
    assert [(d["tipo"], d["id"]) for d in duplicados] == [("conta", conta["id"])]


def test_duplicados_nao_vazam_entre_restaurantes(client_logado, restaurante_id, intruso):
    rid_intruso = intruso.get("/api/restaurantes").json()[0]["id"]
    intruso.post(
        f"{base(rid_intruso)}/despesas", json={"descricao": "Do intruso", "valor": "1234.56", "data": "2026-10-05"}
    )
    enviar(intruso, rid_intruso, [*NOTA, f"CHAVE {CHAVE}"])
    doc = enviar(client_logado, restaurante_id, [*NOTA, f"CHAVE {CHAVE}", "outra linha"])

    assert conferencia(client_logado, restaurante_id, doc["id"])["possiveis_duplicados"] == []
    assert intruso.get(f"{base(rid_intruso)}/documentos/{doc['id']}/conferencia").status_code == 404
