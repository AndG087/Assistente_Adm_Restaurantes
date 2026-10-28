from datetime import date

import pytest

from app.core import tempo
from app.core.config import get_settings
from scripts import criar_demonstracao

HOJE = date(2026, 10, 28)


@pytest.fixture(autouse=True)
def ambiente(monkeypatch, tmp_path):
    monkeypatch.setattr(tempo, "hoje", lambda: HOJE)
    monkeypatch.setattr(get_settings(), "documentos_dir", tmp_path / "demonstracao")


@pytest.fixture
def demonstracao(db, novo_cliente):
    resumo = criar_demonstracao.popular(db, HOJE, "Restaurante Exemplo")
    cliente = novo_cliente()
    resposta = cliente.post(
        "/api/auth/login", json={"email": criar_demonstracao.EMAIL, "senha": criar_demonstracao.SENHA}
    )
    assert resposta.status_code == 200
    return cliente, resumo


def test_cria_um_restaurante_com_seis_meses_de_dados(demonstracao):
    cliente, resumo = demonstracao
    rid = resumo["restaurante_id"]

    assert [r["nome"] for r in cliente.get("/api/restaurantes").json()] == ["Restaurante Exemplo"]
    meses = cliente.get(f"/api/restaurantes/{rid}/relatorios/mensal", params={"meses": 6}).json()["meses"]
    assert all(float(m["valor_total"]) > 0 for m in meses)
    assert resumo["despesas"] > 150


def test_alertas_tem_algo_para_mostrar(demonstracao):
    cliente, resumo = demonstracao

    alertas = cliente.get(f"/api/restaurantes/{resumo['restaurante_id']}/contas-a-pagar/alertas").json()

    assert alertas["vencidas"]["quantidade"] >= 1
    assert alertas["vencem_hoje"]["quantidade"] >= 1
    assert alertas["proximos_dias"]["quantidade"] >= 1


def test_meses_anteriores_estao_pagos(demonstracao):
    cliente, resumo = demonstracao

    vencidas = cliente.get(
        f"/api/restaurantes/{resumo['restaurante_id']}/contas-a-pagar", params={"situacao": "vencidas"}
    ).json()["itens"]

    # Só ficam vencidas as do mês atual escolhidas para a demonstração.
    assert all(c["data_vencimento"] >= "2026-10-01" for c in vencidas)


def test_documentos_esperando_conferencia(demonstracao):
    cliente, resumo = demonstracao
    rid = resumo["restaurante_id"]

    documentos = cliente.get(f"/api/restaurantes/{rid}/documentos").json()

    assert sorted(d["nome_original"] for d in documentos) == [
        "boleto-gas.png", "foto-da-nota-chopp.png", "nfe-distribuidora-chopp.pdf"
    ]
    nota = next(d for d in documentos if d["nome_original"] == "nfe-distribuidora-chopp.pdf")
    assert nota["dados_extraidos"]["valor"] == "2140.00"
    conferencia = cliente.get(f"/api/restaurantes/{rid}/documentos/{nota['id']}/conferencia").json()
    # O fornecedor fictício com o CNPJ de exemplo é reconhecido.
    assert conferencia["fornecedor_sugerido"]["nome"] == "Distribuidora Chopp Gelado"


def test_assistente_responde_com_os_dados_da_demonstracao(demonstracao, fake_ollama):
    cliente, resumo = demonstracao

    resposta = cliente.post(
        f"/api/restaurantes/{resumo['restaurante_id']}/assistente", json={"mensagem": "Quanto gastei com bebidas este mês?"}
    ).json()

    assert resposta["origem"] == "dados"
    assert "na categoria Bebidas somaram R$" in resposta["resposta"]


def test_categoria_de_musica_reconhecida_por_palavra_chave(demonstracao):
    cliente, resumo = demonstracao

    sugestao = cliente.post(
        f"/api/restaurantes/{resumo['restaurante_id']}/sugestoes/categoria", json={"descricao": "Cachê do DJ"}
    ).json()

    assert sugestao["categoria"]["nome"] == "Música ao vivo e eventos"


def test_script_recusa_banco_que_nao_e_de_demonstracao(monkeypatch, capsys):
    monkeypatch.setattr(get_settings(), "database_url", "mysql+pymysql://u:s@localhost/restaurante_admin")
    monkeypatch.setattr("sys.argv", ["criar_demonstracao", "--nome", "X"])

    assert criar_demonstracao.main() == 1
    assert "não termina em '_demo'" in capsys.readouterr().err
