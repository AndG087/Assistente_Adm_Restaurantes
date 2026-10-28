from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.documento import StatusDocumento


class DadosExtraidos(BaseModel):
    """Campos encontrados no texto por regras fixas. São sugestões para a conferência."""

    valor: str | None = None
    data_emissao: str | None = None
    data_vencimento: str | None = None
    cnpj_emitente: str | None = None
    numero_documento: str | None = None
    chave_acesso: str | None = None
    tipo_sugerido: str | None = None


class DocumentoResumo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome_original: str
    tipo_mime: str
    tamanho_bytes: int
    status: StatusDocumento
    metodo_extracao: str | None
    erro: str | None
    dados_extraidos: DadosExtraidos | None
    despesa_id: int | None
    conta_pagar_id: int | None
    criado_em: datetime


class DocumentoDetalhe(DocumentoResumo):
    texto_extraido: str | None
