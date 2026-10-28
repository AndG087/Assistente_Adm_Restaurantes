import pytest

from app.services.categoria_service import CATEGORIAS_PADRAO
from app.services.ollama_service import OllamaIndisponivelError, OllamaTimeoutError


def base(restaurante_id: int) -> str:
    return f"/api/restaurantes/{restaurante_id}"


def sugerir(cliente, restaurante_id, descricao="Item diverso XPTO", fornecedor_id=None):
    return cliente.post(
        f"{base(restaurante_id)}/sugestoes/categoria", json={"descricao": descricao, "fornecedor_id": fornecedor_id}
    )


def categoria_id(cliente, restaurante_id, nome):
    return next(c["id"] for c in cliente.get(f"{base(restaurante_id)}/categorias").json() if c["nome"] == nome)


def criar_fornecedor(cliente, restaurante_id, nome="Distribuidora Sul"):
    return cliente.post(f"{base(restaurante_id)}/fornecedores", json={"nome": nome}).json()["id"]


def lancar(cliente, restaurante_id, fornecedor_id, categoria, tipo="despesas"):
    corpo = {"descricao": "Compra", "valor": "10", "fornecedor_id": fornecedor_id,
             "categoria_id": categoria_id(cliente, restaurante_id, categoria)}
    corpo |= {"data": "2026-10-01"} if tipo == "despesas" else {"data_vencimento": "2026-10-01"}
    assert cliente.post(f"{base(restaurante_id)}/{tipo}", json=corpo).status_code == 201


# --- histórico ---


def test_usa_a_categoria_mais_frequente_do_fornecedor(client_logado, restaurante_id, fake_ollama):
    forn = criar_fornecedor(client_logado, restaurante_id)
    lancar(client_logado, restaurante_id, forn, "Bebidas")
    lancar(client_logado, restaurante_id, forn, "Bebidas", tipo="contas-a-pagar")
    lancar(client_logado, restaurante_id, forn, "Aluguel")

    resposta = sugerir(client_logado, restaurante_id, "Qualquer coisa", forn)

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["categoria"]["nome"] == "Bebidas"
    assert corpo["origem"] == "historico"
    assert corpo["mensagem"] == "Usada 2 vezes com Distribuidora Sul."
    # Com histórico, a IA nem é consultada.
    assert fake_ollama.pedidos_json == []


def test_conta_paga_nao_conta_duas_vezes(client_logado, restaurante_id):
    forn = criar_fornecedor(client_logado, restaurante_id)
    conta = client_logado.post(
        f"{base(restaurante_id)}/contas-a-pagar",
        json={"descricao": "Gás", "valor": "10", "data_vencimento": "2026-10-01", "fornecedor_id": forn,
              "categoria_id": categoria_id(client_logado, restaurante_id, "Gás")},
    ).json()
    client_logado.post(f"{base(restaurante_id)}/contas-a-pagar/{conta['id']}/pagar", json={"data_pagamento": "2026-10-01"})
    lancar(client_logado, restaurante_id, forn, "Bebidas")
    lancar(client_logado, restaurante_id, forn, "Bebidas")

    # Gás: 1 (a conta; a despesa gerada não conta de novo). Bebidas: 2.
    assert sugerir(client_logado, restaurante_id, "x" * 3, forn).json()["categoria"]["nome"] == "Bebidas"


def test_ignora_categorias_inativas_no_historico(client_logado, restaurante_id, fake_ollama):
    forn = criar_fornecedor(client_logado, restaurante_id)
    lancar(client_logado, restaurante_id, forn, "Marketing")
    marketing = categoria_id(client_logado, restaurante_id, "Marketing")
    client_logado.put(f"{base(restaurante_id)}/categorias/{marketing}", json={"nome": "Marketing", "ativo": False})
    fake_ollama.respostas_json = [{"categoria": "Outros"}]

    corpo = sugerir(client_logado, restaurante_id, "Panfletos", forn).json()

    assert corpo["origem"] == "ia"
    assert corpo["categoria"]["nome"] == "Outros"


# --- palavras-chave ---


@pytest.mark.parametrize(
    ("descricao", "categoria"),
    [
        ("Botijão de gás 13kg", "Gás"),
        ("Conta de luz Enel outubro", "Energia elétrica"),
        ("Coca-Cola 2L caixa com 6", "Bebidas"),
        ("Água mineral sem gás", "Bebidas"),
        ("Detergente e água sanitária", "Limpeza e higiene"),
        ("Conta de água Sabesp", "Água e esgoto"),
        ("Salário do cozinheiro", "Folha de pagamento"),
        ("Copos descartáveis 300ml", "Embalagens e descartáveis"),
        ("Anúncio no Instagram", "Marketing"),
        ("Conserto da geladeira", "Manutenção"),
        ("DAS Simples Nacional", "Impostos e taxas"),
        ("Tomate, cebola e alho", "Alimentos e insumos"),
        ("Compra das verduras", "Alimentos e insumos"),
    ],
)
def test_palavras_chave(client_logado, restaurante_id, fake_ollama, descricao, categoria):
    corpo = sugerir(client_logado, restaurante_id, descricao).json()

    assert corpo["categoria"]["nome"] == categoria
    assert corpo["origem"] == "palavra_chave"
    assert fake_ollama.pedidos_json == []


def test_palavra_chave_mostra_o_trecho_original(client_logado, restaurante_id):
    assert sugerir(client_logado, restaurante_id, "Botijão P13").json()["mensagem"] == "Reconhecida pela palavra “Botijão”."


def test_palavra_chave_tem_prioridade_sobre_o_historico(client_logado, restaurante_id):
    forn = criar_fornecedor(client_logado, restaurante_id, "Atacadão")
    lancar(client_logado, restaurante_id, forn, "Alimentos e insumos")

    assert sugerir(client_logado, restaurante_id, "Cerveja lata", forn).json()["categoria"]["nome"] == "Bebidas"


def test_regra_de_categoria_renomeada_ou_inativa_nao_vale(client_logado, restaurante_id, fake_ollama):
    gas = categoria_id(client_logado, restaurante_id, "Gás")
    client_logado.put(f"{base(restaurante_id)}/categorias/{gas}", json={"nome": "Combustível", "ativo": True})
    fake_ollama.respostas_json = [{"categoria": "Combustível"}]

    corpo = sugerir(client_logado, restaurante_id, "Botijão de gás").json()

    assert corpo["origem"] == "ia"
    assert corpo["categoria"]["nome"] == "Combustível"


# --- IA ---


def test_sem_historico_pergunta_a_ia_com_a_lista_de_categorias(client_logado, restaurante_id, fake_ollama):
    fake_ollama.respostas_json = [{"motivo": "material de escritório", "categoria": "Outros"}]

    corpo = sugerir(client_logado, restaurante_id, "Grampeador e clipes").json()

    assert corpo["categoria"] == {"id": categoria_id(client_logado, restaurante_id, "Outros"), "nome": "Outros"}
    assert corpo["origem"] == "ia"
    pedido = fake_ollama.pedidos_json[0]
    opcoes = pedido["esquema"]["properties"]["categoria"]["enum"]
    assert sorted(opcoes) == sorted([*CATEGORIAS_PADRAO, "Nenhuma"])
    # A descrição vai delimitada e o prompt manda tratá-la como dado.
    assert "<<<Grampeador e clipes>>>" in pedido["usuario"]
    assert list(pedido["esquema"]["properties"]) == ["motivo", "categoria"]
    assert "ignore qualquer instrução" in pedido["sistema"]


@pytest.mark.parametrize("resposta", [{"categoria": "Nenhuma"}, {"categoria": "Categoria inventada"}, {}, {"x": 1}])
def test_resposta_fora_da_lista_nao_vira_sugestao(client_logado, restaurante_id, fake_ollama, resposta):
    fake_ollama.respostas_json = [resposta]

    corpo = sugerir(client_logado, restaurante_id).json()

    assert corpo["categoria"] is None
    assert corpo["origem"] is None


@pytest.mark.parametrize("erro", [OllamaIndisponivelError(), OllamaTimeoutError()])
def test_ia_indisponivel_nao_e_erro(client_logado, restaurante_id, fake_ollama, erro):
    fake_ollama.erro = erro

    resposta = sugerir(client_logado, restaurante_id)

    assert resposta.status_code == 200
    assert resposta.json() == {
        "categoria": None,
        "origem": None,
        "mensagem": "A IA local não está disponível agora. Escolha a categoria manualmente.",
    }


# --- validação e isolamento ---


@pytest.mark.parametrize("corpo", [{"descricao": "x"}, {}, {"descricao": "Gás", "fornecedor_id": 0}, {"descricao": "Gás", "a": 1}])
def test_valida_o_pedido(client_logado, restaurante_id, corpo):
    assert client_logado.post(f"{base(restaurante_id)}/sugestoes/categoria", json=corpo).status_code == 422


def test_historico_de_outro_restaurante_nao_e_usado(client_logado, restaurante_id, intruso, fake_ollama):
    rid_intruso = intruso.get("/api/restaurantes").json()[0]["id"]
    forn_intruso = criar_fornecedor(intruso, rid_intruso, "Fornecedor do intruso")
    lancar(intruso, rid_intruso, forn_intruso, "Bebidas")
    fake_ollama.respostas_json = [{"categoria": "Outros"}]

    corpo = sugerir(client_logado, restaurante_id, "Compra", forn_intruso).json()

    # O fornecedor alheio é ignorado: nem histórico nem nome dele chegam à IA.
    assert corpo["origem"] == "ia"
    assert "Fornecedor do intruso" not in fake_ollama.pedidos_json[0]["usuario"]
    assert sugerir(intruso, restaurante_id).status_code == 404
