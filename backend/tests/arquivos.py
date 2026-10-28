"""Gera PDFs e imagens sintéticos para os testes (nenhum documento real é usado)."""

import io

from PIL import Image, ImageDraw, ImageFont


def _escapar(texto: str) -> str:
    return texto.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def pdf_com_texto(linhas: list[str]) -> bytes:
    """PDF mínimo com texto embutido (como um DANFE gerado por sistema)."""
    fluxo = ("BT /F1 12 Tf 50 800 Td 16 TL " + " ".join(f"({_escapar(l)}) Tj T*" for l in linhas) + " ET").encode(
        "cp1252"
    )
    objetos = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        b"<< /Length " + str(len(fluxo)).encode() + b" >>\nstream\n" + fluxo + b"\nendstream",
    ]
    saida = io.BytesIO()
    saida.write(b"%PDF-1.4\n")
    posicoes = []
    for numero, objeto in enumerate(objetos, start=1):
        posicoes.append(saida.tell())
        saida.write(f"{numero} 0 obj\n".encode() + objeto + b"\nendobj\n")
    inicio_xref = saida.tell()
    saida.write(f"xref\n0 {len(objetos) + 1}\n0000000000 65535 f \n".encode())
    for posicao in posicoes:
        saida.write(f"{posicao:010d} 00000 n \n".encode())
    saida.write(f"trailer\n<< /Size {len(objetos) + 1} /Root 1 0 R >>\nstartxref\n{inicio_xref}\n%%EOF\n".encode())
    return saida.getvalue()


def _imagem(linhas: list[str]) -> Image.Image:
    fonte = ImageFont.load_default(size=36)
    imagem = Image.new("RGB", (1400, 60 * len(linhas) + 80), "white")
    desenho = ImageDraw.Draw(imagem)
    for i, linha in enumerate(linhas):
        desenho.text((40, 40 + i * 60), linha, fill="black", font=fonte)
    return imagem


def png_com_texto(linhas: list[str]) -> bytes:
    saida = io.BytesIO()
    _imagem(linhas).save(saida, format="PNG")
    return saida.getvalue()


def pdf_escaneado(linhas: list[str]) -> bytes:
    """PDF só com imagem, sem texto embutido (como um documento passado no scanner)."""
    saida = io.BytesIO()
    _imagem(linhas).save(saida, format="PDF", resolution=150)
    return saida.getvalue()


NOTA = [
    "DISTRIBUIDORA BOA COMIDA LTDA",
    "CNPJ: 11.222.333/0001-81",
    "NOTA FISCAL N 004521",
    "DATA DE EMISSAO: 05/10/2026",
    "VALOR TOTAL DA NOTA R$ 1.234,56",
]
