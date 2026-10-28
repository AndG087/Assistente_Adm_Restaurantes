import pytest

from app.core.config import get_settings
from app.services import extracao_texto
from tests.arquivos import NOTA, pdf_com_texto, pdf_escaneado, png_com_texto

precisa_ocr = pytest.mark.skipif(not extracao_texto.ocr_disponivel(), reason="Tesseract não instalado")


@pytest.fixture(autouse=True)
def pasta_temporaria(monkeypatch, tmp_path):
    """Os testes nunca gravam na pasta real de documentos."""
    monkeypatch.setattr(get_settings(), "documentos_dir", tmp_path)
    return tmp_path


def url(restaurante_id: int, sufixo: str = "") -> str:
    return f"/api/restaurantes/{restaurante_id}/documentos{sufixo}"


def enviar(cliente, restaurante_id, conteudo: bytes, nome="nota.pdf", tipo="application/pdf"):
    return cliente.post(url(restaurante_id), files={"arquivo": (nome, conteudo, tipo)})


# --- envio e extração ---


def test_pdf_com_texto_e_lido_sem_ocr(client_logado, restaurante_id):
    resposta = enviar(client_logado, restaurante_id, pdf_com_texto(NOTA))

    assert resposta.status_code == 201, resposta.text
    doc = resposta.json()
    assert doc["status"] == "pendente"
    assert doc["metodo_extracao"] == "pdf_texto"
    assert doc["tipo_mime"] == "application/pdf"
    assert "VALOR TOTAL DA NOTA" in doc["texto_extraido"]
    assert doc["dados_extraidos"]["valor"] == "1234.56"
    assert doc["dados_extraidos"]["cnpj_emitente"] == "11222333000181"
    assert doc["dados_extraidos"]["numero_documento"] == "4521"


@precisa_ocr
def test_imagem_passa_pelo_ocr(client_logado, restaurante_id):
    resposta = enviar(client_logado, restaurante_id, png_com_texto(NOTA), "foto.png", "image/png")

    doc = resposta.json()
    assert doc["metodo_extracao"] == "ocr"
    assert doc["dados_extraidos"]["valor"] == "1234.56"


@precisa_ocr
def test_pdf_escaneado_passa_pelo_ocr(client_logado, restaurante_id):
    doc = enviar(client_logado, restaurante_id, pdf_escaneado(NOTA)).json()

    assert doc["metodo_extracao"] == "ocr"
    assert doc["dados_extraidos"]["cnpj_emitente"] == "11222333000181"


def test_sem_ocr_o_documento_fica_com_erro_e_pode_ser_reprocessado(client_logado, restaurante_id, monkeypatch):
    monkeypatch.setattr(extracao_texto, "ocr_disponivel", lambda: False)
    doc = enviar(client_logado, restaurante_id, pdf_escaneado(NOTA)).json()

    assert doc["status"] == "erro"
    assert "OCR não está disponível" in doc["erro"]
    assert doc["texto_extraido"] is None

    # Com o OCR "instalado", o reprocessamento extrai o texto.
    monkeypatch.setattr(extracao_texto, "ocr_disponivel", lambda: True)
    monkeypatch.setattr(extracao_texto, "_ocr", lambda imagem: "\n".join(NOTA))
    reprocessado = client_logado.post(url(restaurante_id, f"/{doc['id']}/reprocessar")).json()
    assert reprocessado["status"] == "pendente"
    assert reprocessado["dados_extraidos"]["valor"] == "1234.56"


# --- validações do arquivo ---


def test_tipo_decidido_pelo_conteudo_e_nao_pela_extensao(client_logado, restaurante_id):
    resposta = enviar(client_logado, restaurante_id, b"<script>alert(1)</script>", "nota.pdf", "application/pdf")

    assert resposta.status_code == 415


def test_arquivo_vazio_ou_grande_demais(client_logado, restaurante_id, monkeypatch):
    assert enviar(client_logado, restaurante_id, b"").status_code == 422

    monkeypatch.setattr(get_settings(), "documento_tamanho_maximo_mb", 1)
    grande = b"%PDF-" + b"0" * (1024 * 1024)
    assert enviar(client_logado, restaurante_id, grande).status_code == 413


def test_pdf_corrompido_vira_erro_sem_derrubar(client_logado, restaurante_id):
    resposta = enviar(client_logado, restaurante_id, b"%PDF-1.4\nisto nao e um pdf de verdade")

    assert resposta.status_code == 201
    assert resposta.json()["status"] == "erro"


def test_mesmo_arquivo_nao_entra_duas_vezes(client_logado, restaurante_id):
    conteudo = pdf_com_texto(NOTA)
    primeiro = enviar(client_logado, restaurante_id, conteudo).json()

    repetido = enviar(client_logado, restaurante_id, conteudo, "outro-nome.pdf")

    assert repetido.status_code == 409
    assert repetido.json()["detail"]["documento_id"] == primeiro["id"]


def test_nome_original_nao_vira_caminho(client_logado, restaurante_id, pasta_temporaria):
    doc = enviar(client_logado, restaurante_id, pdf_com_texto(NOTA), "..\\..\\C:\\segredos\\nota.pdf").json()

    assert doc["nome_original"] == "nota.pdf"
    salvos = [p for p in pasta_temporaria.rglob("*") if p.is_file()]
    assert len(salvos) == 1
    assert salvos[0].parent.name == str(restaurante_id)
    assert salvos[0].name != "nota.pdf"


# --- consulta, arquivo e exclusão ---


def test_baixa_o_arquivo_original(client_logado, restaurante_id):
    conteudo = pdf_com_texto(NOTA)
    doc = enviar(client_logado, restaurante_id, conteudo).json()

    resposta = client_logado.get(url(restaurante_id, f"/{doc['id']}/arquivo"))

    assert resposta.status_code == 200
    assert resposta.content == conteudo
    assert resposta.headers["content-type"] == "application/pdf"
    assert resposta.headers["x-content-type-options"] == "nosniff"
    assert resposta.headers["content-disposition"].startswith("inline")


def test_lista_por_status_sem_o_texto(client_logado, restaurante_id, monkeypatch):
    enviar(client_logado, restaurante_id, pdf_com_texto(NOTA))
    monkeypatch.setattr(extracao_texto, "ocr_disponivel", lambda: False)
    enviar(client_logado, restaurante_id, pdf_escaneado(NOTA), "escaneado.pdf")

    pendentes = client_logado.get(url(restaurante_id), params={"status": "pendente"}).json()
    com_erro = client_logado.get(url(restaurante_id), params={"status": "erro"}).json()

    assert [d["nome_original"] for d in pendentes] == ["nota.pdf"]
    assert [d["nome_original"] for d in com_erro] == ["escaneado.pdf"]
    assert "texto_extraido" not in pendentes[0]


def test_exclui_documento_e_o_arquivo(client_logado, restaurante_id, pasta_temporaria):
    doc = enviar(client_logado, restaurante_id, pdf_com_texto(NOTA)).json()

    assert client_logado.delete(url(restaurante_id, f"/{doc['id']}")).status_code == 204
    assert client_logado.get(url(restaurante_id, f"/{doc['id']}")).status_code == 404
    assert not [p for p in pasta_temporaria.rglob("*") if p.is_file()]


def test_isolamento_entre_restaurantes(client_logado, restaurante_id, intruso):
    doc = enviar(client_logado, restaurante_id, pdf_com_texto(NOTA)).json()
    rid_intruso = intruso.get("/api/restaurantes").json()[0]["id"]

    assert intruso.get(url(restaurante_id)).status_code == 404
    assert enviar(intruso, restaurante_id, pdf_com_texto(["outro"])).status_code == 404
    for sufixo in ("", "/arquivo"):
        assert intruso.get(url(rid_intruso, f"/{doc['id']}{sufixo}")).status_code == 404
    assert intruso.delete(url(rid_intruso, f"/{doc['id']}")).status_code == 404
    assert intruso.get(url(rid_intruso)).json() == []
    # O mesmo arquivo pode ser enviado por outro restaurante (a regra de repetição é por restaurante).
    assert enviar(intruso, rid_intruso, pdf_com_texto(NOTA)).status_code == 201


def test_pdf_com_pagina_gigante_e_renderizado_com_teto_de_pixels(monkeypatch):
    from app.services import extracao_texto

    # Página de 5 m x 5 m (14400 pt, o máximo do formato) e sem texto: vai para o OCR.
    pdf = pdf_com_texto([]).replace(b"/MediaBox [0 0 595 842]", b"/MediaBox [0 0 14400 14400]")
    tamanhos = []
    monkeypatch.setattr(extracao_texto, "_ocr", lambda imagem: tamanhos.append(imagem.size) or "")

    extracao_texto.extrair_texto(pdf, "application/pdf")

    largura, altura = tamanhos[0]
    assert largura * altura <= extracao_texto._MAXIMO_PIXELS
    assert largura > 1000  # reduzida, mas ainda legível
