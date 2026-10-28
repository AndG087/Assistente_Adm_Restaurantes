"""Conferência de documentos: sugestões, duplicados e geração do lançamento."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Documento, Fornecedor, StatusDocumento
from app.schemas.conta_pagar import ContaPagarCreate
from app.schemas.despesa import DespesaCreate
from app.schemas.documento import ConfirmacaoDocumento
from app.services import conta_pagar_service, despesa_service, duplicidade
from app.services.duplicidade import PossivelDuplicado
from app.services.erros import OperacaoNaoPermitidaError

_CONFERIVEIS = (StatusDocumento.PENDENTE, StatusDocumento.ERRO)


@dataclass(frozen=True)
class Conferencia:
    fornecedor_sugerido: Fornecedor | None
    duplicados: list[PossivelDuplicado]


def _fornecedor_pelo_cnpj(db: Session, restaurante_id: int, cnpj: str | None) -> Fornecedor | None:
    if not cnpj:
        return None
    return db.scalar(
        select(Fornecedor).where(
            Fornecedor.restaurante_id == restaurante_id, Fornecedor.documento == cnpj, Fornecedor.ativo.is_(True)
        )
    )


def _data(texto: str | None) -> date | None:
    try:
        return date.fromisoformat(texto) if texto else None
    except ValueError:
        return None


def preparar(db: Session, documento: Documento) -> Conferencia:
    dados = documento.dados_extraidos or {}
    fornecedor = _fornecedor_pelo_cnpj(db, documento.restaurante_id, dados.get("cnpj_emitente"))
    valor = Decimal(dados["valor"]) if dados.get("valor") else None
    data = _data(dados.get("data_vencimento")) or _data(dados.get("data_emissao"))
    duplicados = duplicidade.procurar(
        db,
        documento.restaurante_id,
        documento.id,
        documento.chave_acesso,
        dados.get("numero_documento"),
        fornecedor.id if fornecedor else None,
        valor,
        data,
    )
    return Conferencia(fornecedor, duplicados)


def confirmar(db: Session, documento: Documento, usuario_id: int, dados: ConfirmacaoDocumento) -> Documento:
    """Cria a despesa ou a conta com os dados conferidos pelo usuário e marca o documento como concluído."""
    if documento.status not in _CONFERIVEIS:
        raise OperacaoNaoPermitidaError("Este documento já foi conferido ou descartado.")

    campos = dados.model_dump(exclude={"tipo", "data"})
    if dados.tipo == "despesa":
        despesa = despesa_service.criar(
            db, documento.restaurante_id, usuario_id, DespesaCreate(**campos, data=dados.data)
        )
        documento.despesa_id = despesa.id
    else:
        conta = conta_pagar_service.criar(
            db, documento.restaurante_id, usuario_id, ContaPagarCreate(**campos, data_vencimento=dados.data)
        )
        documento.conta_pagar_id = conta.id
    documento.status = StatusDocumento.CONCLUIDO
    db.commit()
    db.refresh(documento)
    return documento


def descartar(db: Session, documento: Documento) -> Documento:
    if documento.status not in _CONFERIVEIS:
        raise OperacaoNaoPermitidaError("Só documentos ainda não conferidos podem ser descartados.")
    documento.status = StatusDocumento.DESCARTADO
    db.commit()
    db.refresh(documento)
    return documento
