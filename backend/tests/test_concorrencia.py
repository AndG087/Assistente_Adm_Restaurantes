"""Pedidos repetidos ao mesmo tempo (clique duplo, duas abas, reenvio) não podem duplicar nada."""

import threading
import time
from collections.abc import Callable

from fastapi.testclient import TestClient

from app.services import conferencia_service, conta_pagar_service, extracao_texto
from tests.arquivos import pdf_com_texto

NOTA = pdf_com_texto(["NOTA FISCAL 4521", "VALOR TOTAL R$ 1.234,56"])


def _mesma_sessao(novo_cliente: Callable[[], TestClient], cliente: TestClient) -> TestClient:
    """Outro cliente com o mesmo cookie: simula uma segunda aba do mesmo usuário."""
    outro = novo_cliente()
    outro.cookies.update(cliente.cookies)
    return outro


def _ao_mesmo_tempo(*chamadas: Callable[[], object]) -> list[object]:
    barreira = threading.Barrier(len(chamadas))
    resultados: list[object] = [None] * len(chamadas)

    def rodar(indice: int, chamada: Callable[[], object]) -> None:
        barreira.wait()
        try:
            resultados[indice] = chamada()
        except Exception as erro:  # erro 500 vira exceção no TestClient
            resultados[indice] = erro

    threads = [threading.Thread(target=rodar, args=item) for item in enumerate(chamadas)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return resultados


def _devagar(monkeypatch, modulo, nome: str) -> None:
    """Alarga a janela entre a checagem e o commit, para a corrida acontecer sempre."""
    original = getattr(modulo, nome)

    def lenta(*args, **kwargs):
        resultado = original(*args, **kwargs)
        time.sleep(0.5)
        return resultado

    monkeypatch.setattr(modulo, nome, lenta)


def _codigos(resultados: list[object]) -> list[object]:
    return sorted((getattr(r, "status_code", repr(r)) for r in resultados), key=str)


def _enviar(cliente: TestClient, restaurante_id: int):
    return cliente.post(
        f"/api/restaurantes/{restaurante_id}/documentos",
        files={"arquivo": ("nota.pdf", NOTA, "application/pdf")},
    )


def _total_despesas(cliente: TestClient, restaurante_id: int) -> int:
    return cliente.get(f"/api/restaurantes/{restaurante_id}/despesas").json()["total"]


def test_confirmar_documento_duas_vezes_gera_um_lancamento(client_logado, restaurante_id, novo_cliente, monkeypatch):
    documento = _enviar(client_logado, restaurante_id).json()
    _devagar(monkeypatch, conferencia_service.despesa_service, "novo")
    outra_aba = _mesma_sessao(novo_cliente, client_logado)
    url = f"/api/restaurantes/{restaurante_id}/documentos/{documento['id']}/confirmar"
    corpo = {"tipo": "despesa", "descricao": "Compra NF 4521", "valor": "1234.56", "data": "2026-10-05"}

    resultados = _ao_mesmo_tempo(lambda: client_logado.post(url, json=corpo), lambda: outra_aba.post(url, json=corpo))

    assert _codigos(resultados) == [200, 409]
    assert _total_despesas(client_logado, restaurante_id) == 1


def test_pagar_conta_duas_vezes_gera_uma_despesa(client_logado, restaurante_id, novo_cliente, monkeypatch):
    base = f"/api/restaurantes/{restaurante_id}/contas-a-pagar"
    conta = client_logado.post(
        base, json={"descricao": "Aluguel", "valor": "3000.00", "data_vencimento": "2026-10-10"}
    ).json()
    _devagar(monkeypatch, conta_pagar_service, "_garantir_pendente")
    outra_aba = _mesma_sessao(novo_cliente, client_logado)
    url = f"{base}/{conta['id']}/pagar"

    resultados = _ao_mesmo_tempo(lambda: client_logado.post(url, json={}), lambda: outra_aba.post(url, json={}))

    assert _codigos(resultados) == [200, 409]
    assert _total_despesas(client_logado, restaurante_id) == 1


def test_enviar_mesmo_arquivo_duas_vezes_responde_409(client_logado, restaurante_id, novo_cliente, monkeypatch):
    _devagar(monkeypatch, extracao_texto, "extrair_texto")
    outra_aba = _mesma_sessao(novo_cliente, client_logado)

    resultados = _ao_mesmo_tempo(lambda: _enviar(client_logado, restaurante_id), lambda: _enviar(outra_aba, restaurante_id))

    assert _codigos(resultados) == [201, 409]
    repetido = next(r for r in resultados if r.status_code == 409)
    assert "já foi enviado" in repetido.json()["detail"]["mensagem"]
