from app.core import database


def test_health_com_banco_disponivel(client, monkeypatch):
    monkeypatch.setattr(database, "verificar_conexao", lambda: True)

    resposta = client.get("/api/health")

    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok", "banco_de_dados": "ok"}


def test_health_continua_respondendo_com_banco_indisponivel(client, monkeypatch):
    monkeypatch.setattr(database, "verificar_conexao", lambda: False)

    resposta = client.get("/api/health")

    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok", "banco_de_dados": "indisponivel"}
