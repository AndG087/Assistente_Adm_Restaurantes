import pytest

from app.schemas.ia import TAMANHO_MAXIMO_MENSAGEM
from app.services.ollama_service import (
    OllamaError,
    OllamaIndisponivelError,
    OllamaModeloNaoEncontradoError,
    OllamaTimeoutError,
    StatusOllama,
)

# --- GET /api/ia/status ---


def test_status_com_ollama_e_modelo_disponiveis(client_logado):
    resposta = client_logado.get("/api/ia/status")

    assert resposta.status_code == 200
    assert resposta.json() == {
        "ollama_disponivel": True,
        "modelo": "modelo-teste:1b",
        "modelo_disponivel": True,
    }


def test_status_com_ollama_desligado_responde_200(client_logado, fake_ollama):
    fake_ollama.status_atual = StatusOllama(ollama_disponivel=False, modelo="modelo-teste:1b", modelo_disponivel=False)

    resposta = client_logado.get("/api/ia/status")

    assert resposta.status_code == 200
    assert resposta.json()["ollama_disponivel"] is False
    assert resposta.json()["modelo_disponivel"] is False


def test_status_nao_exige_login_mas_so_mostra_o_modelo_para_quem_esta_logado(client):
    resposta = client.get("/api/ia/status")

    assert resposta.status_code == 200
    assert resposta.json() == {"ollama_disponivel": True, "modelo": None, "modelo_disponivel": True}


# --- POST /api/ia/chat: autenticação ---


def test_chat_exige_login(client, fake_ollama):
    resposta = client.post("/api/ia/chat", json={"mensagem": "Olá"})

    assert resposta.status_code == 401
    assert fake_ollama.mensagens_recebidas == []


# --- POST /api/ia/chat: validação ---


@pytest.mark.parametrize(
    "corpo",
    [
        {},
        {"mensagem": ""},
        {"mensagem": "   \n\t "},
        {"mensagem": 123},
        {"mensagem": None},
        {"mensagem": "x" * (TAMANHO_MAXIMO_MENSAGEM + 1)},
        {"mensagem": "oi", "campo_extra": "nao permitido"},
    ],
)
def test_chat_rejeita_requisicao_invalida(client_logado, fake_ollama, corpo):
    resposta = client_logado.post("/api/ia/chat", json=corpo)

    assert resposta.status_code == 422
    assert fake_ollama.mensagens_recebidas == []


def test_chat_aceita_mensagem_no_tamanho_maximo(client_logado):
    resposta = client_logado.post("/api/ia/chat", json={"mensagem": "x" * TAMANHO_MAXIMO_MENSAGEM})

    assert resposta.status_code == 200


def test_chat_remove_espacos_das_pontas(client_logado, fake_ollama):
    client_logado.post("/api/ia/chat", json={"mensagem": "  Olá  "})

    assert fake_ollama.mensagens_recebidas == ["Olá"]


# --- POST /api/ia/chat: sucesso e erros ---


def test_chat_retorna_resposta_do_modelo(client_logado):
    resposta = client_logado.post("/api/ia/chat", json={"mensagem": "Olá"})

    assert resposta.status_code == 200
    assert resposta.json() == {"resposta": "Olá! Como posso ajudar?", "modelo": "modelo-teste:1b"}


@pytest.mark.parametrize(
    ("erro", "status_esperado", "trecho_da_mensagem"),
    [
        (OllamaIndisponivelError("detalhe interno"), 503, "não está acessível"),
        (OllamaModeloNaoEncontradoError("detalhe interno"), 503, "não está instalado"),
        (OllamaTimeoutError("detalhe interno"), 504, "demorou demais"),
        (OllamaError("detalhe interno"), 502, "resposta inesperada"),
    ],
)
def test_chat_converte_falhas_do_ollama_em_erros_controlados(
    client_logado, fake_ollama, erro, status_esperado, trecho_da_mensagem
):
    fake_ollama.erro = erro

    resposta = client_logado.post("/api/ia/chat", json={"mensagem": "Olá"})

    assert resposta.status_code == status_esperado
    detalhe = resposta.json()["detail"]
    assert trecho_da_mensagem in detalhe
    assert "detalhe interno" not in detalhe
    assert "resposta" not in resposta.json()


def test_backend_continua_funcionando_apos_falha_do_ollama(client_logado, fake_ollama):
    fake_ollama.erro = OllamaIndisponivelError()
    assert client_logado.post("/api/ia/chat", json={"mensagem": "Olá"}).status_code == 503

    assert client_logado.get("/api/ia/status").status_code == 200
    fake_ollama.erro = None
    assert client_logado.post("/api/ia/chat", json={"mensagem": "Olá"}).status_code == 200
