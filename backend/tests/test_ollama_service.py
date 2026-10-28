"""Testes do serviço de integração com o Ollama, usando um transporte HTTP simulado."""

import json

import httpx
import pytest

from app.services.ollama_service import (
    PROMPT_DO_SISTEMA,
    OllamaError,
    OllamaIndisponivelError,
    OllamaModeloNaoEncontradoError,
    OllamaService,
    OllamaTimeoutError,
)

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


class Relogio:
    def __init__(self) -> None:
        self.agora = 1000.0

    def __call__(self) -> float:
        return self.agora


def criar_servico(handler, modelo="llama3.2:1b", relogio=None) -> OllamaService:
    return OllamaService(
        base_url="http://ollama.teste",
        modelo=modelo,
        timeout_segundos=5,
        timeout_status_segundos=1,
        cache_status_segundos=10,
        transport=httpx.MockTransport(handler),
        relogio=relogio or Relogio(),
    )


def resposta_tags(*nomes: str) -> httpx.Response:
    return httpx.Response(200, json={"models": [{"name": n, "model": n} for n in nomes]})


# --- status ---


async def test_status_com_modelo_instalado():
    servico = criar_servico(lambda req: resposta_tags("llama3.2:1b", "outro:7b"))

    status = await servico.status()

    assert status.ollama_disponivel is True
    assert status.modelo_disponivel is True
    assert status.modelo == "llama3.2:1b"


async def test_status_sem_o_modelo_configurado():
    servico = criar_servico(lambda req: resposta_tags("outro:7b"))

    status = await servico.status()

    assert status.ollama_disponivel is True
    assert status.modelo_disponivel is False


async def test_status_considera_tag_latest_implicita():
    servico = criar_servico(lambda req: resposta_tags("llama3.2:latest"), modelo="llama3.2")

    assert (await servico.status()).modelo_disponivel is True


async def test_status_com_ollama_desligado():
    def handler(req):
        raise httpx.ConnectError("conexão recusada")

    status = await criar_servico(handler).status()

    assert status.ollama_disponivel is False
    assert status.modelo_disponivel is False


async def test_status_com_timeout():
    def handler(req):
        raise httpx.ConnectTimeout("demorou")

    assert (await criar_servico(handler).status()).ollama_disponivel is False


async def test_status_com_resposta_que_nao_e_json():
    servico = criar_servico(lambda req: httpx.Response(200, text="isto não é json"))

    assert (await servico.status()).ollama_disponivel is False


async def test_status_usa_cache_e_expira():
    chamadas = []
    relogio = Relogio()

    def handler(req):
        chamadas.append(req.url.path)
        return resposta_tags("llama3.2:1b")

    servico = criar_servico(handler, relogio=relogio)

    await servico.status()
    await servico.status()
    assert chamadas == ["/api/tags"]

    relogio.agora += 11
    await servico.status()
    assert len(chamadas) == 2


# --- conversar ---


async def test_conversar_envia_requisicao_correta_e_retorna_texto():
    recebido = {}

    def handler(req):
        recebido["caminho"] = req.url.path
        recebido["corpo"] = json.loads(req.content)
        return httpx.Response(200, json={"message": {"role": "assistant", "content": "  Olá!  "}, "done": True})

    resposta = await criar_servico(handler).conversar("Oi")

    assert resposta == "Olá!"
    assert recebido["caminho"] == "/api/chat"
    assert recebido["corpo"]["model"] == "llama3.2:1b"
    assert recebido["corpo"]["stream"] is False
    assert recebido["corpo"]["messages"] == [
        {"role": "system", "content": PROMPT_DO_SISTEMA},
        {"role": "user", "content": "Oi"},
    ]


async def test_conversar_com_ollama_desligado():
    def handler(req):
        raise httpx.ConnectError("conexão recusada")

    with pytest.raises(OllamaIndisponivelError):
        await criar_servico(handler).conversar("Oi")


async def test_conversar_com_timeout():
    def handler(req):
        raise httpx.ReadTimeout("demorou")

    with pytest.raises(OllamaTimeoutError):
        await criar_servico(handler).conversar("Oi")


async def test_conversar_com_modelo_inexistente():
    servico = criar_servico(lambda req: httpx.Response(404, json={"error": "model 'llama3.2:1b' not found"}))

    with pytest.raises(OllamaModeloNaoEncontradoError):
        await servico.conversar("Oi")


async def test_conversar_com_erro_interno_do_ollama():
    servico = criar_servico(lambda req: httpx.Response(500, json={"error": "falhou"}))

    with pytest.raises(OllamaError):
        await servico.conversar("Oi")


@pytest.mark.parametrize(
    "resposta",
    [
        httpx.Response(200, text="não é json"),
        httpx.Response(200, json={"sem_message": True}),
        httpx.Response(200, json={"message": {"content": "   "}}),
        httpx.Response(200, json={"message": {"content": None}}),
    ],
)
async def test_conversar_rejeita_resposta_invalida(resposta):
    with pytest.raises(OllamaError):
        await criar_servico(lambda req: resposta).conversar("Oi")


async def test_gerar_json_envia_o_esquema_e_le_a_resposta():
    recebido = {}
    esquema = {"type": "object", "properties": {"categoria": {"type": "string", "enum": ["Gás", "Nenhuma"]}}}

    def handler(req):
        recebido["corpo"] = json.loads(req.content)
        return httpx.Response(200, json={"message": {"content": '{"categoria": "Gás"}'}})

    resultado = await criar_servico(handler).gerar_json("sistema", "usuário", esquema)

    assert resultado == {"categoria": "Gás"}
    assert recebido["corpo"]["format"] == esquema
    assert recebido["corpo"]["options"] == {"temperature": 0}
    assert recebido["corpo"]["messages"] == [
        {"role": "system", "content": "sistema"},
        {"role": "user", "content": "usuário"},
    ]


@pytest.mark.parametrize("conteudo", ["não é json", "[1, 2]", '"texto"'])
async def test_gerar_json_rejeita_resposta_que_nao_e_objeto(conteudo):
    servico = criar_servico(lambda req: httpx.Response(200, json={"message": {"content": conteudo}}))

    with pytest.raises(OllamaError):
        await servico.gerar_json("s", "u", {})


async def test_falha_no_chat_invalida_cache_de_status():
    chamadas_tags = []
    ollama_ligado = True

    def handler(req):
        if not ollama_ligado:
            raise httpx.ConnectError("conexão recusada")
        chamadas_tags.append(1)
        return resposta_tags("llama3.2:1b")

    servico = criar_servico(handler)
    assert (await servico.status()).ollama_disponivel is True

    ollama_ligado = False
    with pytest.raises(OllamaIndisponivelError):
        await servico.conversar("Oi")

    # Sem esperar o cache expirar, o status já reflete a queda.
    assert (await servico.status()).ollama_disponivel is False
