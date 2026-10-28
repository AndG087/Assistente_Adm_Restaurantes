from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Path, UploadFile, status
from fastapi.responses import FileResponse

from app.api.deps import DbSession, UsuarioAtual, VinculoRestaurante
from app.core.config import get_settings
from app.models import Documento, StatusDocumento
from app.schemas.documento import DocumentoDetalhe, DocumentoResumo
from app.services import armazenamento, documento_service
from app.services.erros import OperacaoNaoPermitidaError

router = APIRouter(prefix="/restaurantes/{restaurante_id}/documentos", tags=["Documentos"])

IdPositivo = Annotated[int, Path(gt=0)]


def _obter_ou_404(db: DbSession, vinculo: VinculoRestaurante, documento_id: int) -> Documento:
    documento = documento_service.obter(db, vinculo.restaurante_id, documento_id)
    if documento is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Documento não encontrado.")
    return documento


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
    try:
        return documento_service.reprocessar(db, documento, vinculo.restaurante.cnpj)
    except OperacaoNaoPermitidaError as erro:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(erro)) from None


@router.delete("/{documento_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir(db: DbSession, vinculo: VinculoRestaurante, documento_id: IdPositivo) -> None:
    documento = _obter_ou_404(db, vinculo, documento_id)
    try:
        documento_service.excluir(db, documento)
    except OperacaoNaoPermitidaError as erro:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(erro)) from None
