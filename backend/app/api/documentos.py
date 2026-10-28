from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Path, UploadFile, status
from fastapi.responses import FileResponse

from app.api.deps import DbSession, UsuarioAtual, VinculoRestaurante, ou_404
from app.core.config import get_settings
from app.models import Documento, StatusDocumento
from app.schemas.documento import (
    ConferenciaResponse,
    ConfirmacaoDocumento,
    DocumentoDetalhe,
    DocumentoResumo,
    PossivelDuplicadoResponse,
)
from app.schemas.financeiro import Referencia
from app.services import armazenamento, conferencia_service, documento_service

router = APIRouter(prefix="/restaurantes/{restaurante_id}/documentos", tags=["Documentos"])

IdPositivo = Annotated[int, Path(gt=0)]


def _obter_ou_404(db: DbSession, vinculo: VinculoRestaurante, documento_id: int) -> Documento:
    return ou_404(documento_service.obter(db, vinculo.restaurante_id, documento_id), "Documento não encontrado.")


@router.get("", response_model=list[DocumentoResumo])
def listar(db: DbSession, vinculo: VinculoRestaurante, status: StatusDocumento | None = None) -> list[Documento]:
    return documento_service.listar(db, vinculo.restaurante_id, status)


# Função síncrona: o FastAPI a executa em outra thread, então o OCR (que pode levar segundos)
# não trava o atendimento das demais requisições.
@router.post("", response_model=DocumentoDetalhe, status_code=status.HTTP_201_CREATED)
def enviar(
    db: DbSession,
    vinculo: VinculoRestaurante,
    usuario: UsuarioAtual,
    arquivo: Annotated[UploadFile, File(description="PDF, JPG ou PNG")],
) -> Documento:
    limite = get_settings().documento_tamanho_maximo_mb * 1024 * 1024
    # Lê no máximo limite + 1 byte: basta para saber se passou do limite sem carregar um arquivo enorme.
    conteudo = arquivo.file.read(limite + 1)
    if len(conteudo) > limite:
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"O arquivo passa de {get_settings().documento_tamanho_maximo_mb} MB.",
        )
    if not conteudo:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail="O arquivo está vazio.")
    try:
        return documento_service.enviar(db, vinculo.restaurante, usuario.id, arquivo.filename, conteudo)
    except documento_service.ArquivoInvalidoError as erro:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(erro)) from None
    except documento_service.DocumentoRepetidoError as erro:
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail={"mensagem": str(erro), "documento_id": erro.existente.id}
        ) from None


@router.get("/{documento_id}", response_model=DocumentoDetalhe)
def obter(db: DbSession, vinculo: VinculoRestaurante, documento_id: IdPositivo) -> Documento:
    return _obter_ou_404(db, vinculo, documento_id)


@router.get("/{documento_id}/arquivo", response_class=FileResponse)
def baixar_arquivo(db: DbSession, vinculo: VinculoRestaurante, documento_id: IdPositivo) -> FileResponse:
    documento = _obter_ou_404(db, vinculo, documento_id)
    caminho = armazenamento.caminho(documento.arquivo)
    if not caminho.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="O arquivo deste documento não foi encontrado.")
    return FileResponse(
        caminho,
        media_type=documento.tipo_mime,
        filename=documento.nome_original,
        content_disposition_type="inline",  # o navegador mostra o PDF/imagem na tela de conferência
        headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store"},
    )


@router.post("/{documento_id}/reprocessar", response_model=DocumentoDetalhe)
def reprocessar(db: DbSession, vinculo: VinculoRestaurante, documento_id: IdPositivo) -> Documento:
    documento = _obter_ou_404(db, vinculo, documento_id)
    return documento_service.reprocessar(db, documento, vinculo.restaurante.cnpj)


@router.get("/{documento_id}/conferencia", response_model=ConferenciaResponse)
def conferencia(db: DbSession, vinculo: VinculoRestaurante, documento_id: IdPositivo) -> ConferenciaResponse:
    """Fornecedor reconhecido pelo CNPJ e lançamentos que podem ser o mesmo documento."""
    resultado = conferencia_service.preparar(db, _obter_ou_404(db, vinculo, documento_id))
    fornecedor = resultado.fornecedor_sugerido
    return ConferenciaResponse(
        fornecedor_sugerido=Referencia.model_validate(fornecedor) if fornecedor else None,
        possiveis_duplicados=[PossivelDuplicadoResponse.model_validate(d) for d in resultado.duplicados],
    )


@router.post("/{documento_id}/confirmar", response_model=DocumentoDetalhe)
def confirmar(
    dados: ConfirmacaoDocumento,
    db: DbSession,
    vinculo: VinculoRestaurante,
    usuario: UsuarioAtual,
    documento_id: IdPositivo,
) -> Documento:
    documento = _obter_ou_404(db, vinculo, documento_id)
    return conferencia_service.confirmar(db, documento, usuario.id, dados)


@router.post("/{documento_id}/descartar", response_model=DocumentoDetalhe)
def descartar(db: DbSession, vinculo: VinculoRestaurante, documento_id: IdPositivo) -> Documento:
    documento = _obter_ou_404(db, vinculo, documento_id)
    return conferencia_service.descartar(db, documento)


@router.delete("/{documento_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir(db: DbSession, vinculo: VinculoRestaurante, documento_id: IdPositivo) -> None:
    documento = _obter_ou_404(db, vinculo, documento_id)
    documento_service.excluir(db, documento)
