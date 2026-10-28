import pytest

from tests.conftest import registrar


def url(restaurante_id: int, sufixo: str = "") -> str:
    return f"/api/restaurantes/{restaurante_id}/membros{sufixo}"


@pytest.fixture
def bruno(novo_cliente):
    cliente = novo_cliente()
    registrar(cliente, email="bruno@exemplo.com", nome="Bruno Lima")
    cliente.usuario_id = cliente.get("/api/auth/eu").json()["id"]
    return cliente


def adicionar(dono, restaurante_id, email="bruno@exemplo.com", papel="membro"):
    return dono.post(url(restaurante_id), json={"email": email, "papel": papel})


def test_lista_comeca_com_o_proprietario(client_logado, restaurante_id):
    assert client_logado.get(url(restaurante_id)).json() == [
        {
            "usuario_id": client_logado.get("/api/auth/eu").json()["id"],
            "nome": "Ana Souza",
            "email": "ana@exemplo.com",
            "papel": "proprietario",
            "voce": True,
        }
    ]


def test_membro_adicionado_passa_a_ver_os_dados(client_logado, restaurante_id, bruno):
    client_logado.post(
        f"/api/restaurantes/{restaurante_id}/despesas", json={"descricao": "Compra", "valor": "10", "data": "2026-10-01"}
    )
    assert bruno.get(f"/api/restaurantes/{restaurante_id}/despesas").status_code == 404

    resposta = adicionar(client_logado, restaurante_id, email=" BRUNO@exemplo.com ")

    assert resposta.status_code == 201
    assert resposta.json()["papel"] == "membro"
    assert resposta.json()["voce"] is False
    assert [r["nome"] for r in bruno.get("/api/restaurantes").json()] == ["Cantina da Ana"]
    assert bruno.get(f"/api/restaurantes/{restaurante_id}/despesas").json()["total"] == 1


def test_erros_ao_adicionar(client_logado, restaurante_id, bruno):
    sem_conta = adicionar(client_logado, restaurante_id, email="ninguem@exemplo.com")
    assert sem_conta.status_code == 422
    assert "Não existe conta com este e-mail" in sem_conta.json()["detail"]

    assert adicionar(client_logado, restaurante_id, email="invalido").status_code == 422
    assert adicionar(client_logado, restaurante_id, papel="administrador").status_code == 422
    assert adicionar(client_logado, restaurante_id).status_code == 201
    assert adicionar(client_logado, restaurante_id).status_code == 409


def test_membro_nao_gerencia_a_equipe(client_logado, restaurante_id, bruno, novo_cliente):
    adicionar(client_logado, restaurante_id)
    carla = novo_cliente()
    registrar(carla, email="carla@exemplo.com", nome="Carla")
    ana_id = client_logado.get("/api/auth/eu").json()["id"]

    assert bruno.get(url(restaurante_id)).status_code == 200
    assert adicionar(bruno, restaurante_id, email="carla@exemplo.com").status_code == 403
    assert bruno.put(url(restaurante_id, f"/{bruno.usuario_id}"), json={"papel": "proprietario"}).status_code == 403
    assert bruno.delete(url(restaurante_id, f"/{ana_id}")).status_code == 403


def test_promover_rebaixar_e_ultimo_proprietario(client_logado, restaurante_id, bruno):
    adicionar(client_logado, restaurante_id)
    ana_id = client_logado.get("/api/auth/eu").json()["id"]

    # Sozinha como proprietária, Ana não pode se rebaixar nem sair.
    assert client_logado.put(url(restaurante_id, f"/{ana_id}"), json={"papel": "membro"}).status_code == 409
    assert client_logado.delete(url(restaurante_id, f"/{ana_id}")).status_code == 409

    promovido = client_logado.put(url(restaurante_id, f"/{bruno.usuario_id}"), json={"papel": "proprietario"})
    assert promovido.json()["papel"] == "proprietario"

    # Com outro proprietário, Ana pode deixar de ser.
    assert client_logado.put(url(restaurante_id, f"/{ana_id}"), json={"papel": "membro"}).status_code == 200
    assert [r["papel"] for r in client_logado.get("/api/restaurantes").json()] == ["membro"]


def test_remover_e_sair(client_logado, restaurante_id, bruno):
    adicionar(client_logado, restaurante_id)

    assert client_logado.delete(url(restaurante_id, f"/{bruno.usuario_id}")).status_code == 204
    assert bruno.get(f"/api/restaurantes/{restaurante_id}").status_code == 404

    adicionar(client_logado, restaurante_id)
    # O próprio membro pode sair.
    assert bruno.delete(url(restaurante_id, f"/{bruno.usuario_id}")).status_code == 204
    assert bruno.get("/api/restaurantes").json() == []


def test_isolamento(client_logado, restaurante_id, intruso, bruno):
    assert intruso.get(url(restaurante_id)).status_code == 404
    assert adicionar(intruso, restaurante_id, email="intruso@exemplo.com").status_code == 404
    rid_intruso = intruso.get("/api/restaurantes").json()[0]["id"]
    # Mexer em alguém que não é da equipe do próprio restaurante.
    assert intruso.delete(url(rid_intruso, f"/{bruno.usuario_id}")).status_code == 404


def test_limita_emails_sem_conta_para_nao_servir_de_consulta(client_logado, restaurante_id, bruno, monkeypatch):
    from app.api import membros as rotas_membros

    monkeypatch.setattr(rotas_membros.emails_nao_encontrados, "maximo", 3)
    codigos = [adicionar(client_logado, restaurante_id, email=f"teste{i}@exemplo.com").status_code for i in range(4)]
    assert codigos == [422, 422, 422, 429]

    # Bloqueado, nem um e-mail que existe é testado: a resposta não revela nada.
    bloqueado = adicionar(client_logado, restaurante_id)
    assert bloqueado.status_code == 429
    assert "Muitos e-mails não encontrados" in bloqueado.json()["detail"]
