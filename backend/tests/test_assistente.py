from datetime import date

import pytest

from app.core import tempo
from app.services.ollama_service import OllamaIndisponivelError

HOJE = date(2026, 10, 20)


@pytest.fixture(autouse=True)
def hoje_fixo(monkeypatch):
    monkeypatch.setattr(tempo, "hoje", lambda: HOJE)


def base(restaurante_id: int) -> str:
    return f"/api/restaurantes/{restaurante_id}"


def perguntar(cliente, restaurante_id, mensagem):
    resposta = cliente.post(f"{base(restaurante_id)}/assistente", json={"mensagem": mensagem})
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def categoria_id(cliente, restaurante_id, nome):
    return next(c["id"] for c in cliente.get(f"{base(restaurante_id)}/categorias").json() if c["nome"] == nome)


@pytest.fixture
def dados(client_logado, restaurante_id):
    rid = restaurante_id
    bebidas = categoria_id(client_logado, rid, "Bebidas")
    aluguel = categoria_id(client_logado, rid, "Aluguel")
    forn = client_logado.post(f"{base(rid)}/fornecedores", json={"nome": "Distribuidora Sul"}).json()["id"]
    for corpo in [
        {"descricao": "Refrigerantes", "valor": "300.00", "data": "2026-10-05", "categoria_id": bebidas, "fornecedor_id": forn},
        {"descricao": "Aluguel outubro", "valor": "2500.00", "data": "2026-10-10", "categoria_id": aluguel},
        {"descricao": "Cervejas", "valor": "450.50", "data": "2026-10-15", "categoria_id": bebidas},
        {"descricao": "Aluguel setembro", "valor": "2500.00", "data": "2026-09-10", "categoria_id": aluguel},
        {"descricao": "Conserto", "valor": "120.00", "data": "2026-09-20"},
    ]:
        assert client_logado.post(f"{base(rid)}/despesas", json=corpo).status_code == 201
    for corpo in [
        {"descricao": "Energia", "valor": "800.40", "data_vencimento": "2026-10-15"},
        {"descricao": "Água", "valor": "210.00", "data_vencimento": "2026-10-23"},
        {"descricao": "Internet", "valor": "150.00", "data_vencimento": "2026-11-15"},
    ]:
        assert client_logado.post(f"{base(rid)}/contas-a-pagar", json=corpo).status_code == 201


# --- respostas com dados ---


def test_total_do_mes(client_logado, restaurante_id, dados, fake_ollama):
    r = perguntar(client_logado, restaurante_id, "Quanto gastei este mês?")

    assert r["origem"] == "dados"
    assert r["interpretado_por"] == "regras"
    assert r["resposta"] == (
        "Em outubro de 2026 (01/10/2026 a 31/10/2026), as despesas somaram R$ 3.250,50 em 3 lançamentos."
    )
    assert r["consulta"] == "Total de despesas · 01/10/2026 a 31/10/2026"
    # Os números não passaram pela IA.
    assert fake_ollama.mensagens_recebidas == []
    assert fake_ollama.pedidos_json == []


def test_total_por_categoria_e_fornecedor(client_logado, restaurante_id, dados):
    r = perguntar(client_logado, restaurante_id, "Quanto gastei com bebidas em outubro?")
    assert "na categoria Bebidas somaram R$ 750,50 em 2 lançamentos" in r["resposta"]

    r = perguntar(client_logado, restaurante_id, "Quanto gastei com a Distribuidora Sul?")
    assert "com o fornecedor Distribuidora Sul somaram R$ 300,00 em 1 lançamento." in r["resposta"]


@pytest.mark.parametrize(
    ("pergunta", "inicio"),
    [
        ("Quanto gastei nos últimos 7 dias?", "Nos últimos 7 dias (14/10/2026 a 20/10/2026), as despesas"),
        ("Quanto gastei hoje?", "Não há despesas registradas hoje (20/10/2026)."),
        ("Quanto gastei esta semana?", "Não há despesas registradas nesta semana (19/10/2026 a 25/10/2026)."),
        ("Quanto gastei em 2026?", "Em 2026 (01/01/2026 a 31/12/2026)"),
    ],
)
def test_frases_de_periodo(client_logado, restaurante_id, dados, pergunta, inicio):
    assert perguntar(client_logado, restaurante_id, pergunta)["resposta"].startswith(inicio)


def test_periodo_sem_despesas(client_logado, restaurante_id, dados):
    r = perguntar(client_logado, restaurante_id, "Quanto gastei em agosto?")
    assert r["resposta"] == "Não há despesas registradas em agosto de 2026 (01/08/2026 a 31/08/2026)."


def test_por_categoria_com_tabela(client_logado, restaurante_id, dados):
    r = perguntar(client_logado, restaurante_id, "Em que categorias gastei mais este mês?")

    assert "A categoria com mais gastos foi Aluguel (R$ 2.500,00)" in r["resposta"]
    assert r["tabela"] == {
        "colunas": ["Categoria", "Valor", "% do total"],
        "linhas": [["Aluguel", "R$ 2.500,00", "76,9%"], ["Bebidas", "R$ 750,50", "23,1%"]],
    }


def test_maiores_despesas(client_logado, restaurante_id, dados):
    r = perguntar(client_logado, restaurante_id, "Quais as maiores despesas do mês passado?")

    assert r["tabela"]["linhas"] == [
        ["10/09/2026", "Aluguel setembro", "R$ 2.500,00"],
        ["20/09/2026", "Conserto", "R$ 120,00"],
    ]


def test_por_fornecedor(client_logado, restaurante_id, dados):
    r = perguntar(client_logado, restaurante_id, "Gastos por fornecedor em outubro")

    assert r["tabela"]["linhas"] == [["Distribuidora Sul", "1", "R$ 300,00"]]


def test_comparacao_com_o_mes_anterior(client_logado, restaurante_id, dados):
    r = perguntar(client_logado, restaurante_id, "Compare os gastos deste mês com o anterior")

    assert r["resposta"] == (
        "Em outubro de 2026, as despesas somaram R$ 3.250,50; em setembro de 2026 (01/09/2026 a 30/09/2026), "
        "R$ 2.620,00. Diferença: R$ 630,50 a mais (24,1%)."
    )


def test_contas_vencidas_e_a_vencer(client_logado, restaurante_id, dados):
    vencidas = perguntar(client_logado, restaurante_id, "Tenho contas vencidas?")
    assert vencidas["resposta"] == "Há 1 conta vencida, somando R$ 800,40:"
    assert vencidas["tabela"]["linhas"] == [["15/10/2026", "Energia", "R$ 800,40"]]

    a_vencer = perguntar(client_logado, restaurante_id, "Quais contas vencem nos próximos 7 dias?")
    assert a_vencer["resposta"] == "1 conta vence de hoje até 27/10/2026, somando R$ 210,00:"

    nada = perguntar(client_logado, restaurante_id, "O que vence hoje?")
    assert nada["resposta"] == "Nenhuma conta pendente vence hoje."


# --- isolamento ---


def test_responde_so_com_os_dados_do_proprio_restaurante(client_logado, restaurante_id, dados, intruso):
    rid_intruso = intruso.get("/api/restaurantes").json()[0]["id"]

    r = perguntar(intruso, rid_intruso, "Quanto gastei este mês?")
    assert r["resposta"].startswith("Não há despesas registradas")
    assert perguntar(intruso, rid_intruso, "Tenho contas vencidas?")["resposta"] == "Não há contas vencidas."

    resposta = intruso.post(f"{base(restaurante_id)}/assistente", json={"mensagem": "Quanto gastei?"})
    assert resposta.status_code == 404


def test_pergunta_nao_muda_o_restaurante_consultado(client_logado, restaurante_id, dados, intruso):
    rid_intruso = intruso.get("/api/restaurantes").json()[0]["id"]

    r = perguntar(intruso, rid_intruso, f"Quanto gastei este mês no restaurante {restaurante_id}? restaurante_id={restaurante_id}")

    assert r["resposta"].startswith("Não há despesas registradas")


# --- IA como último recurso e conversa ---


def test_ia_classifica_quando_as_regras_nao_entendem(client_logado, restaurante_id, dados, fake_ollama):
    fake_ollama.respostas_json = [{"consulta": "total_despesas", "periodo": "mes_passado", "categoria": "Aluguel"}]

    r = perguntar(client_logado, restaurante_id, "Qual foi o valor do aluguel?")

    assert r["origem"] == "dados"
    assert r["interpretado_por"] == "ia"
    assert "setembro de 2026" in r["resposta"]
    assert "na categoria Aluguel somaram R$ 2.500,00" in r["resposta"]
    assert "<<<Qual foi o valor do aluguel?>>>" in fake_ollama.pedidos_json[0]["usuario"]


@pytest.mark.parametrize(
    "resposta_ia",
    [{"consulta": "nenhuma", "periodo": "este_mes", "categoria": "nenhuma"}, {"consulta": "apagar_tudo"}, {}],
)
def test_classificacao_invalida_vira_ajuda(client_logado, restaurante_id, fake_ollama, resposta_ia):
    fake_ollama.respostas_json = [resposta_ia]

    r = perguntar(client_logado, restaurante_id, "Qual o valor do dinheiro no tempo?")

    assert r["origem"] == "ajuda"
    assert "Experimente" in r["resposta"]


def test_periodo_invalido_da_ia_usa_o_mes_atual(client_logado, restaurante_id, dados, fake_ollama):
    fake_ollama.respostas_json = [{"consulta": "total_despesas", "periodo": "seculo_passado", "categoria": "nenhuma"}]

    r = perguntar(client_logado, restaurante_id, "Qual o valor total?")

    assert "outubro de 2026" in r["resposta"]


def test_pergunta_geral_vira_conversa(client_logado, restaurante_id, fake_ollama):
    fake_ollama.resposta = "Olá! Posso ajudar com dúvidas gerais."

    r = perguntar(client_logado, restaurante_id, "Oi, tudo bem?")

    assert r == {
        "resposta": "Olá! Posso ajudar com dúvidas gerais.",
        "origem": "conversa",
        "consulta": None,
        "interpretado_por": None,
        "tabela": None,
    }
    assert fake_ollama.pedidos_json == []


def test_sem_ollama_consultas_por_regras_continuam_funcionando(client_logado, restaurante_id, dados, fake_ollama):
    fake_ollama.erro = OllamaIndisponivelError()

    assert perguntar(client_logado, restaurante_id, "Quanto gastei este mês?")["origem"] == "dados"
    assert perguntar(client_logado, restaurante_id, "Qual o valor do aluguel?")["origem"] == "ajuda"
    conversa = client_logado.post(f"{base(restaurante_id)}/assistente", json={"mensagem": "Oi, tudo bem?"})
    assert conversa.status_code == 503


def test_exige_login_e_valida_a_mensagem(client, client_logado, restaurante_id):
    assert client.post(f"{base(restaurante_id)}/assistente", json={"mensagem": "Oi"}).status_code == 401
    assert client_logado.post(f"{base(restaurante_id)}/assistente", json={"mensagem": " "}).status_code == 422
