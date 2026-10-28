"""Extração do TEXTO de documentos (PDF e imagens). Não interpreta nada: isso fica em interpretacao_documento.

- PDF com texto embutido (ex.: DANFE gerado por sistema): lido diretamente, sem OCR.
- PDF escaneado ou foto: cada página vira imagem e passa pelo Tesseract, executado localmente.
"""

import io
import logging
import re
import shutil
import subprocess
import warnings
from dataclasses import dataclass
from pathlib import Path

import pypdfium2
from PIL import Image, ImageOps
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Abaixo disso, o texto embutido no PDF é considerado ausente (PDF escaneado) e o OCR é usado.
_MINIMO_CARACTERES_PDF = 40
# Imagens maiores que isso são recusadas (proteção contra "bombas de descompressão").
_MAXIMO_PIXELS = 50_000_000
_DPI_OCR = 300

# Assinaturas (primeiros bytes) dos formatos aceitos. O tipo é decidido pelo conteúdo, não pela extensão.
_ASSINATURAS = [
    (b"%PDF-", "application/pdf", ".pdf"),
    (b"\xff\xd8\xff", "image/jpeg", ".jpg"),
    (b"\x89PNG\r\n\x1a\n", "image/png", ".png"),
]


class ExtracaoError(Exception):
    """Não foi possível extrair o texto. A mensagem pode ser exibida ao usuário."""


@dataclass(frozen=True)
class ResultadoExtracao:
    texto: str
    metodo: str  # "pdf_texto" ou "ocr"


def detectar_tipo(conteudo: bytes) -> tuple[str, str] | None:
    """(tipo MIME, extensão) a partir do conteúdo, ou None se o formato não for aceito."""
    for assinatura, mime, extensao in _ASSINATURAS:
        if conteudo.startswith(assinatura):
            return mime, extensao
    return None


def ocr_disponivel() -> bool:
    settings = get_settings()
    executavel = Path(settings.tesseract_cmd)
    tem_executavel = executavel.is_file() or shutil.which(settings.tesseract_cmd) is not None
    tem_idioma = (settings.tessdata_dir / f"{settings.ocr_idioma}.traineddata").is_file()
    return tem_executavel and tem_idioma


def extrair_texto(conteudo: bytes, tipo_mime: str) -> ResultadoExtracao:
    if tipo_mime == "application/pdf":
        return _extrair_pdf(conteudo)
    return ResultadoExtracao(_ocr(_abrir_imagem(conteudo)), "ocr")


def _limpar(texto: str) -> str:
    # Remove espaços no fim das linhas e excesso de linhas em branco, preservando a estrutura.
    linhas = [linha.rstrip() for linha in texto.replace("\r", "").split("\n")]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(linhas)).strip()


def _extrair_pdf(conteudo: bytes) -> ResultadoExtracao:
    maximo = get_settings().ocr_maximo_paginas
    try:
        leitor = PdfReader(io.BytesIO(conteudo))
        if leitor.is_encrypted and not leitor.decrypt(""):
            raise ExtracaoError("O PDF está protegido por senha.")
        paginas = leitor.pages[:maximo]
        texto = _limpar("\n\n".join(pagina.extract_text() or "" for pagina in paginas))
    except PdfReadError as erro:
        raise ExtracaoError("O PDF está corrompido ou não pôde ser lido.") from erro

    if len(re.sub(r"\s", "", texto)) >= _MINIMO_CARACTERES_PDF:
        return ResultadoExtracao(texto, "pdf_texto")

    # Sem texto embutido: renderiza as páginas e aplica OCR.
    try:
        pdf = pypdfium2.PdfDocument(conteudo)
    except pypdfium2.PdfiumError as erro:
        raise ExtracaoError("O PDF está corrompido ou não pôde ser lido.") from erro
    try:
        textos = []
        for indice in range(min(len(pdf), maximo)):
            pagina = pdf[indice]
            imagem = pagina.render(scale=_escala_ocr(*pagina.get_size())).to_pil()
            textos.append(_ocr(imagem))
    finally:
        pdf.close()
    return ResultadoExtracao(_limpar("\n\n".join(textos)), "ocr")


def _escala_ocr(largura_pt: float, altura_pt: float) -> float:
    """Escala para renderizar a página a 300 DPI, reduzida se a imagem passaria de _MAXIMO_PIXELS.

    O tamanho da página vem do próprio PDF: sem este teto, uma página declarada com metros de
    lado viraria uma imagem de bilhões de pixels e esgotaria a memória.
    """
    escala = _DPI_OCR / 72
    pixels = largura_pt * altura_pt * escala * escala
    if pixels > _MAXIMO_PIXELS:
        # 0,999: o renderizador arredonda largura e altura para cima.
        escala *= (_MAXIMO_PIXELS / pixels) ** 0.5 * 0.999
    return escala


def _abrir_imagem(conteudo: bytes) -> Image.Image:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            imagem = Image.open(io.BytesIO(conteudo))
            if imagem.width * imagem.height > _MAXIMO_PIXELS:
                raise ExtracaoError("A imagem é grande demais.")
            imagem.load()
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as erro:
        raise ExtracaoError("A imagem é grande demais.") from erro
    except OSError as erro:
        raise ExtracaoError("A imagem está corrompida ou não pôde ser lida.") from erro
    # Fotos de celular guardam a rotação em metadados (EXIF); o OCR precisa da imagem já girada.
    return ImageOps.exif_transpose(imagem)


def _preparar_para_ocr(imagem: Image.Image) -> bytes:
    imagem = imagem.convert("L")  # tons de cinza
    # Imagens pequenas (ex.: foto de baixa resolução) são ampliadas: o Tesseract erra menos.
    if imagem.width < 1200:
        fator = 1200 / imagem.width
        imagem = imagem.resize((1200, round(imagem.height * fator)), Image.Resampling.LANCZOS)
    saida = io.BytesIO()
    imagem.save(saida, format="PNG")
    return saida.getvalue()


def _ocr(imagem: Image.Image) -> str:
    settings = get_settings()
    if not ocr_disponivel():
        raise ExtracaoError(
            "O OCR não está disponível neste computador (Tesseract ou idioma português não encontrado)."
        )
    comando = [
        settings.tesseract_cmd,
        "stdin",
        "stdout",
        "-l",
        settings.ocr_idioma,
        "--tessdata-dir",
        str(settings.tessdata_dir),
        "--psm",
        "3",  # segmentação automática da página
    ]
    try:
        resultado = subprocess.run(
            comando,
            input=_preparar_para_ocr(imagem),
            capture_output=True,
            timeout=settings.ocr_timeout_segundos,
            check=False,
        )
    except subprocess.TimeoutExpired as erro:
        raise ExtracaoError("O OCR demorou demais para ler o documento.") from erro
    if resultado.returncode != 0:
        logger.warning("Tesseract terminou com código %s", resultado.returncode)
        raise ExtracaoError("O OCR não conseguiu ler o documento.")
    return _limpar(resultado.stdout.decode("utf-8", errors="replace"))
