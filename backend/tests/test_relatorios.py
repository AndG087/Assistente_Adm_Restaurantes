import csv
import io
from datetime import date

import pytest

from app.core import tempo

HOJE = date(2026, 10, 20)


@pytest.fixture(autouse=True)
def hoje_fixo(monkeypatch):
    monkeypatch.setattr(tempo, "hoje", lambda: HOJE)


def base(restaurante_id: int) -> str:
    return f"/api/restaurantes/{restaurante_id}/relatorios"


def despesa(cliente, restaurante_id, **campos):
    corpo = {"descricao": "Compra", "valor": "10", "data": "2026-10-01"} | campos
    resposta = cliente.post(f"/api/restaurantes/{restaurante_id}/despesas", json=corpo)
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def ler_csv(resposta) -> list[list[str]]:
    texto = resposta.content.decode("utf-8")
    assert texto.startswith("﻿")  # BOM para o Excel reconhecer UTF-8
    return list(csv.reader(io.StringIO(texto[1:]), delimiter=";"))


# --- evolução mensal ---


def test_evolucao_mensal_com_meses_vazios(client_logado, restaurante_id):
    despesa(client_logado, restaurante_id, valor="100.00", data="2026-08-05")
    despesa(client_logado, restaurante_id, valor="50.50", data="2026-08-25")
    despesa(client_logado, restaurante_id, valor="300.00", data="2026-10-02")
    despesa(client_logado, restaurante_id, valor="999.00", data="2026-06-30")  # fora da janela de 4 meses

    corpo = client_logado.get(f"{base(restaurante_id)}/mensal", params={"meses": 4}).json()

    assert [(m["rotulo"], m["quantidade"], m["valor_total"]) for m in corpo["meses"]] == [
        ("jul/2026", 0, "0.00"),
        ("ago/2026", 2, "150.50"),
        ("set/2026", 0, "0.00"),
        ("out/2026", 1, "300.00"),
    ]
    # Média dos 3 meses completos (jul, ago, set): 150,50 / 3.
    assert corpo["media_mensal"] == "50.17"


def test_evolucao_atravessa_a_virada_do_ano(client_logado, restaurante_id, monkeypatch):
    monkeypatch.setattr(tempo, "hoje", lambda: date(2027, 1, 10))
    despesa(client_logado, restaurante_id, valor="10", data="2026-12-31")

    meses = client_logado.get(f"{base(restaurante_id)}/mensal", params={"meses": 2}).json()["meses"]

    assert [(m["rotulo"], m["valor_total"]) for m in meses] == [("dez/2026", "10.00"), ("jan/2027", "0.00")]


def test_quantidade_de_meses_validada(client_logado, restaurante_id):
    assert client_logado.get(f"{base(restaurante_id)}/mensal", params={"meses": 1}).status_code == 422
    assert client_logado.get(f"{base(restaurante_id)}/mensal", params={"meses": 25}).status_code == 422


# --- por fornecedor ---


def test_totais_por_fornecedor(client_logado, restaurante_id):
    sul = client_logado.post(f"/api/restaurantes/{restaurante_id}/fornecedores", json={"nome": "Sul"}).json()["id"]
    norte = client_logado.post(f"/api/restaurantes/{restaurante_id}/fornecedores", json={"nome": "Norte"}).json()["id"]
    despesa(client_logado, restaurante_id, valor="100", fornecedor_id=sul)
    despesa(client_logado, restaurante_id, valor="250", fornecedor_id=norte)
    despesa(client_logado, restaurante_id, valor="40")
    despesa(client_logado, restaurante_id, valor="999", fornecedor_id=sul, data="2026-09-01")

    corpo = client_logado.get(
        f"{base(restaurante_id)}/fornecedores", params={"de": "2026-10-01", "ate": "2026-10-31"}
    ).json()

    assert [(f["fornecedor"]["nome"] if f["fornecedor"] else None, f["quantidade"], f["valor_total"]) for f in corpo] == [
        ("Norte", 1, "250.00"),
        ("Sul", 1, "100.00"),
        (None, 1, "40.00"),
    ]


# --- CSV ---


def test_csv_de_despesas(client_logado, restaurante_id):
    despesa(client_logado, restaurante_id, descricao="Cervejas", valor="1234.5", data="2026-10-05", numero_documento="NF 9")
    despesa(client_logado, restaurante_id, descricao="Fora do período", data="2026-09-01")

    resposta = client_logado.get(f"{base(restaurante_id)}/despesas.csv", params={"de": "2026-10-01", "ate": "2026-10-31"})

    assert resposta.status_code == 200
    assert resposta.headers["content-type"] == "text/csv; charset=utf-8"
    assert resposta.headers["content-disposition"] == 'attachment; filename="despesas_2026-10-01_2026-10-31.csv"'
    assert ler_csv(resposta) == [
        ["Data", "Descrição", "Categoria", "Fornecedor", "Nº documento", "Valor (R$)", "Observações"],
        ["05/10/2026", "Cervejas", "", "", "NF 9", "1234,50", ""],
    ]


def test_csv_neutraliza_formulas(client_logado, restaurante_id):
    despesa(client_logado, restaurante_id, descricao='=HYPERLINK("http://mal.example","clique")')
    despesa(client_logado, restaurante_id, descricao="+55 telefone", observacoes="@SUM(A1)")

    linhas = ler_csv(client_logado.get(f"{base(restaurante_id)}/despesas.csv"))

    descricoes = {linha[1] for linha in linhas[1:]}
    assert "'=HYPERLINK(\"http://mal.example\",\"clique\")" in descricoes
    assert "'+55 telefone" in descricoes
    assert any(linha[6] == "'@SUM(A1)" for linha in linhas[1:])


def test_csv_traz_todas_as_paginas(client_logado, restaurante_id, db):
    from app.models import Despesa

    db.add_all(
        Despesa(restaurante_id=restaurante_id, descricao=f"Item {i}", valor=1, data=date(2026, 10, 1))
        for i in range(250)
    )
    db.commit()

    linhas = ler_csv(client_logado.get(f"{base(restaurante_id)}/despesas.csv"))

    assert len(linhas) == 251  # cabeçalho + 250 (a listagem da API para em 200 por página)


def test_csv_de_contas_com_situacao(client_logado, restaurante_id):
    contas = f"/api/restaurantes/{restaurante_id}/contas-a-pagar"
    paga = client_logado.post(contas, json={"descricao": "Gás", "valor": "380", "data_vencimento": "2026-10-10"}).json()
    client_logado.post(f"{contas}/{paga['id']}/pagar", json={"data_pagamento": "2026-10-09"})
    client_logado.post(contas, json={"descricao": "Energia", "valor": "800.4", "data_vencimento": "2026-10-15"})

    resposta = client_logado.get(f"{base(restaurante_id)}/contas.csv")

    assert 'filename="contas_todas_tudo.csv"' in resposta.headers["content-disposition"]
    assert ler_csv(resposta)[1:] == [
        ["10/10/2026", "Gás", "", "", "", "380,00", "Paga", "09/10/2026"],
        ["15/10/2026", "Energia", "", "", "", "800,40", "Vencida", ""],
    ]


# --- isolamento ---


def test_relatorios_isolados(client_logado, restaurante_id, intruso):
    despesa(client_logado, restaurante_id, descricao="Segredo", valor="500")
    rid_intruso = intruso.get("/api/restaurantes").json()[0]["id"]

    for sufixo in ("/mensal", "/fornecedores", "/despesas.csv", "/contas.csv"):
        assert intruso.get(f"{base(restaurante_id)}{sufixo}").status_code == 404
    assert "Segredo" not in intruso.get(f"{base(rid_intruso)}/despesas.csv").text
    assert intruso.get(f"{base(rid_intruso)}/mensal").json()["meses"][-1]["valor_total"] == "0.00"
