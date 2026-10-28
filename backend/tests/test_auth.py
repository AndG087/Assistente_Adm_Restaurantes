from datetime import timedelta

import pytest
from sqlalchemy import select, update

from app.core.tempo import agora_utc
from app.models import Sessao, Usuario
from tests.conftest import registrar

SENHA = "senha-segura-123"


# --- cadastro ---


def test_registro_cria_usuario_e_ja_inicia_a_sessao(client, db):
    resposta = client.post(
        "/api/auth/registrar", json={"nome": "  Ana   Souza ", "email": " Ana@Exemplo.COM ", "senha": SENHA}
    )

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["nome"] == "Ana Souza"
    assert corpo["email"] == "ana@exemplo.com"
    assert "senha" not in str(corpo)

    cookie = resposta.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "samesite=lax" in cookie

    assert client.get("/api/auth/eu").json()["email"] == "ana@exemplo.com"

    usuario = db.scalar(select(Usuario))
    assert usuario.senha_hash.startswith("scrypt$")
    assert SENHA not in usuario.senha_hash


def test_token_puro_nao_fica_no_banco(client, db):
    registrar(client)
    token = client.cookies["sessao"]

    sessao = db.scalar(select(Sessao))
    assert sessao.token_hash != token
    assert token not in sessao.token_hash


def test_registro_com_email_repetido_retorna_409(client, novo_cliente):
    registrar(client, email="ana@exemplo.com")

    resposta = novo_cliente().post(
        "/api/auth/registrar", json={"nome": "Outra Ana", "email": "ANA@exemplo.com", "senha": SENHA}
    )

    assert resposta.status_code == 409


@pytest.mark.parametrize(
    "corpo",
    [
        {"nome": "Ana", "email": "sem-arroba", "senha": SENHA},
        {"nome": "Ana", "email": "ana@exemplo", "senha": SENHA},
        {"nome": "Ana", "email": "ana@exemplo.com", "senha": "curta"},
        {"nome": " ", "email": "ana@exemplo.com", "senha": SENHA},
        {"nome": "Ana", "email": "ana@exemplo.com", "senha": "x" * 129},
        {"nome": "Ana", "email": "ana@exemplo.com"},
        {"nome": "Ana", "email": "ana@exemplo.com", "senha": SENHA, "ativo": False},
    ],
)
def test_registro_rejeita_dados_invalidos(client, corpo):
    assert client.post("/api/auth/registrar", json=corpo).status_code == 422


# --- login e logout ---


def test_login_com_credenciais_corretas(client, novo_cliente):
    registrar(client)
    outro = novo_cliente()

    resposta = outro.post("/api/auth/login", json={"email": "ANA@exemplo.com ", "senha": SENHA})

    assert resposta.status_code == 200
    assert outro.get("/api/auth/eu").status_code == 200


@pytest.mark.parametrize(
    ("email", "senha"),
    [("ana@exemplo.com", "senha-errada"), ("ninguem@exemplo.com", SENHA)],
)
def test_login_invalido_tem_a_mesma_resposta_para_email_e_senha(client, novo_cliente, email, senha):
    registrar(client)
    outro = novo_cliente()

    resposta = outro.post("/api/auth/login", json={"email": email, "senha": senha})

    assert resposta.status_code == 401
    assert resposta.json() == {"detail": "E-mail ou senha inválidos."}
    assert outro.get("/api/auth/eu").status_code == 401


def test_usuario_inativo_nao_consegue_entrar(client, novo_cliente, db):
    registrar(client)
    db.execute(update(Usuario).values(ativo=False))
    db.commit()

    assert novo_cliente().post("/api/auth/login", json={"email": "ana@exemplo.com", "senha": SENHA}).status_code == 401
    # A sessão que já existia também deixa de valer.
    assert client.get("/api/auth/eu").status_code == 401


def test_logout_encerra_a_sessao_no_servidor(client, db):
    registrar(client)
    token = client.cookies["sessao"]

    assert client.post("/api/auth/logout").status_code == 204

    assert db.scalar(select(Sessao)) is None
    # Mesmo reapresentando o token antigo, o acesso é negado.
    client.cookies.set("sessao", token)
    assert client.get("/api/auth/eu").status_code == 401


def test_logout_sem_sessao_nao_falha(client):
    assert client.post("/api/auth/logout").status_code == 204


# --- sessão ---


def test_rotas_protegidas_sem_cookie_ou_com_token_falso(client):
    assert client.get("/api/auth/eu").status_code == 401

    client.cookies.set("sessao", "token-inventado")
    assert client.get("/api/auth/eu").status_code == 401


def test_sessao_expirada_nao_vale(client, db):
    registrar(client)
    db.execute(update(Sessao).values(expira_em=agora_utc() - timedelta(seconds=1)))
    db.commit()

    assert client.get("/api/auth/eu").status_code == 401


# --- limite de tentativas ---


def _login(cliente, senha, email="ana@exemplo.com"):
    return cliente.post("/api/auth/login", json={"email": email, "senha": senha})


def test_login_bloqueia_depois_de_muitas_senhas_erradas(client_logado, client):
    codigos = [_login(client, f"errada-{i}").status_code for i in range(5)]
    assert codigos == [401] * 5

    bloqueado = _login(client, SENHA)  # nem a senha certa entra durante o bloqueio
    assert bloqueado.status_code == 429
    assert "Muitas tentativas" in bloqueado.json()["detail"]
    assert int(bloqueado.headers["retry-after"]) > 0


def test_bloqueio_de_um_email_nao_afeta_outra_conta(client_logado, novo_cliente, client):
    registrar(novo_cliente(), email="bia@exemplo.com", nome="Bia")
    for i in range(5):
        _login(client, f"errada-{i}")

    assert _login(client, SENHA, email="bia@exemplo.com").status_code == 200


def test_login_certo_zera_as_falhas(client_logado, client):
    for i in range(4):
        _login(client, f"errada-{i}")
    assert _login(client, SENHA).status_code == 200
    for i in range(4):
        assert _login(client, f"errada-de-novo-{i}").status_code == 401


def test_cadastro_tem_limite_por_ip(client, monkeypatch):
    from app.api import auth as rotas_auth

    monkeypatch.setattr(rotas_auth.cadastros_por_ip, "maximo", 2)
    corpo = {"nome": "Pessoa", "senha": SENHA}
    codigos = [
        client.post("/api/auth/registrar", json=corpo | {"email": f"p{i}@exemplo.com"}).status_code for i in range(3)
    ]
    assert codigos == [201, 201, 429]
