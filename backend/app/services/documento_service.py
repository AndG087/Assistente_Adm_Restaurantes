"""Documentos enviados: armazenamento, extração do texto e interpretação inicial."""

import hashlib
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.tempo import agora_utc
from app.models import Documento, Restaurante, StatusDocumento
from app.services import armazenamento, extracao_texto, interpretacao_documento
from app.services.erros import OperacaoNaoPermitidaError, RegistroDuplicadoError

logger = logging.getLogger(__name__)


class ArquivoInvalidoError(Exception):
    pass


class DocumentoRepetidoError(RegistroDuplicadoError):
    def __init__(self, existente: Documento) -> None:
        super().__init__(f'Este arquivo já foi enviado ("{existente.nome_original}").')
        self.existente = existente


def _nome_seguro(nome: str | None) -> str:
    # Só para exibição: remove caminhos ("C:\\pasta\\nota.pdf" → "nota.pdf") e caracteres de controle.
    nome = (nome or "documento").replace("\\", "/").rsplit("/", 1)[-1]
    nome = "".join(c for c in nome if c.isprintable()).strip()
    return (nome or "documento")[:255]


def enviar(db: Session, restaurante: Restaurante, usuario_id: int, nome: str | None, conteudo: bytes) -> Documento:
    tipo = extracao_texto.detectar_tipo(conteudo)
    if tipo is None:
        raise ArquivoInvalidoError("Formato não aceito. Envie um PDF, JPG ou PNG.")
    tipo_mime, extensao = tipo

    sha256 = hashlib.sha256(conteudo).hexdigest()
    existente = db.scalar(
        select(Documento).where(Documento.restaurante_id == restaurante.id, Documento.sha256 == sha256)
    )
    if existente is not None:
        raise DocumentoRepetidoError(existente)

    documento = Documento(
        restaurante_id=restaurante.id,
        nome_original=_nome_seguro(nome),
        tipo_mime=tipo_mime,
        tamanho_bytes=len(conteudo),
        sha256=sha256,
        arquivo=armazenamento.salvar(restaurante.id, conteudo, extensao),
        status=StatusDocumento.PENDENTE,
        enviado_por_id=usuario_id,
    )
    _processar(documento, conteudo, restaurante.cnpj)
    db.add(documento)
    try:
        db.commit()
    except Exception:
        # Se o registro não foi gravado, o arquivo não pode ficar órfão no disco.
        db.rollback()
        armazenamento.remover(documento.arquivo)
        raise
    db.refresh(documento)
    return documento


def _processar(documento: Documento, conteudo: bytes, cnpj_do_restaurante: str | None) -> None:
    """Extrai o texto e interpreta. Falhas viram status ERRO com mensagem, nunca exceção."""
    documento.processado_em = agora_utc()
    try:
        resultado = extracao_texto.extrair_texto(conteudo, documento.tipo_mime)
    except extracao_texto.ExtracaoError as erro:
        documento.status = StatusDocumento.ERRO
        documento.erro = str(erro)[:300]
        documento.texto_extraido = None
        documento.metodo_extracao = None
        documento.dados_extraidos = None
        return
    except Exception:
        # Arquivo malformado de um jeito inesperado: registra sem o conteúdo e segue.
        logger.exception("Falha inesperada ao extrair texto do documento")
        documento.status = StatusDocumento.ERRO
        documento.erro = "Não foi possível ler o documento."
        return

    documento.texto_extraido = resultado.texto
    documento.metodo_extracao = resultado.metodo
    documento.erro = None
    documento.status = StatusDocumento.PENDENTE
    if not resultado.texto.strip():
        documento.dados_extraidos = None
        documento.erro = "Nenhum texto foi encontrado no documento."
        return
    dados = interpretacao_documento.interpretar(resultado.texto, cnpj_do_restaurante)
    documento.dados_extraidos = dados
    documento.chave_acesso = dados.get("chave_acesso")


def reprocessar(db: Session, documento: Documento, cnpj_do_restaurante: str | None) -> Documento:
    """Repete a extração (útil depois de instalar o OCR ou para um documento com erro)."""
    if documento.status in (StatusDocumento.CONCLUIDO, StatusDocumento.DESCARTADO):
        raise OperacaoNaoPermitidaError("Só documentos pendentes ou com erro podem ser processados de novo.")
    _processar(documento, armazenamento.ler(documento.arquivo), cnpj_do_restaurante)
    db.commit()
    db.refresh(documento)
    return documento


def listar(db: Session, restaurante_id: int, status: StatusDocumento | None) -> list[Documento]:
    consulta = select(Documento).where(Documento.restaurante_id == restaurante_id)
    if status is not None:
        consulta = consulta.where(Documento.status == status)
    return list(db.scalars(consulta.order_by(Documento.criado_em.desc(), Documento.id.desc()).limit(200)))


def obter(db: Session, restaurante_id: int, documento_id: int) -> Documento | None:
    return db.scalar(
        select(Documento).where(Documento.id == documento_id, Documento.restaurante_id == restaurante_id)
    )


def excluir(db: Session, documento: Documento) -> None:
    # Documento conferido é o comprovante do lançamento: não é apagado.
    if documento.status == StatusDocumento.CONCLUIDO:
        raise OperacaoNaoPermitidaError("Documentos já conferidos são mantidos como comprovante.")
    arquivo = documento.arquivo
    db.delete(documento)
    db.commit()
    armazenamento.remover(arquivo)
