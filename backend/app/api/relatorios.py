from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, status

from app.api.deps import DbSession, VinculoRestaurante
from app.core import tempo
from app.schemas.conta_pagar import FiltroSituacao
from app.schemas.financeiro import Referencia
from app.schemas.relatorio import EvolucaoMensal, TotalFornecedor, TotalMesResponse
from app.services import relatorio_service
from app.services.conta_pagar_service import FiltroContas
from app.services.despesa_service import FiltroDespesas

router = APIRouter(prefix="/restaurantes/{restaurante_id}/relatorios", tags=["Relatórios"])


def _validar_periodo(de: date | None, ate: date | None) -> None:
    if de and ate and de > ate:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail="A data inicial é posterior à final.")


def _csv(conteudo: str, nome: str) -> Response:
    return Response(
        content=conteudo.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nome}"', "Cache-Control": "private, no-store"},
    )


def _sufixo(de: date | None, ate: date | None) -> str:
    return "_".join(d.isoformat() for d in (de, ate) if d) or "tudo"


@router.get("/mensal", response_model=EvolucaoMensal)
def mensal(
    db: DbSession, vinculo: VinculoRestaurante, meses: Annotated[int, Query(ge=2, le=24)] = 12
) -> EvolucaoMensal:
    totais = relatorio_service.evolucao_mensal(db, vinculo.restaurante_id, tempo.hoje(), meses)
    completos = totais[:-1]
    media = sum((t.valor for t in completos), Decimal(0)) / len(completos)
    return EvolucaoMensal(
        meses=[
            TotalMesResponse(ano=t.ano, mes=t.mes, rotulo=t.rotulo, quantidade=t.quantidade, valor_total=t.valor)
            for t in totais
        ],
        media_mensal=media.quantize(Decimal("0.01")),
    )


@router.get("/fornecedores", response_model=list[TotalFornecedor])
def fornecedores(
    db: DbSession, vinculo: VinculoRestaurante, de: date | None = None, ate: date | None = None
) -> list[TotalFornecedor]:
    _validar_periodo(de, ate)
    return [
        TotalFornecedor(
            fornecedor=Referencia.model_validate(f) if f else None, quantidade=quantidade, valor_total=valor
        )
        for f, quantidade, valor in relatorio_service.por_fornecedor(db, vinculo.restaurante_id, de, ate)
    ]


@router.get("/despesas.csv", response_class=Response)
def despesas_csv(
    db: DbSession,
    vinculo: VinculoRestaurante,
    de: date | None = None,
    ate: date | None = None,
    categoria_id: Annotated[int | None, Query(gt=0)] = None,
    sem_categoria: bool = False,
    fornecedor_id: Annotated[int | None, Query(gt=0)] = None,
    busca: Annotated[str | None, Query(max_length=100)] = None,
) -> Response:
    _validar_periodo(de, ate)
    filtro = FiltroDespesas(de, ate, categoria_id, sem_categoria, fornecedor_id, (busca or "").strip() or None)
    conteudo = relatorio_service.despesas_csv(db, vinculo.restaurante_id, filtro)
    return _csv(conteudo, f"despesas_{_sufixo(de, ate)}.csv")


@router.get("/contas.csv", response_class=Response)
def contas_csv(
    db: DbSession,
    vinculo: VinculoRestaurante,
    situacao: FiltroSituacao = FiltroSituacao.TODAS,
    de: date | None = None,
    ate: date | None = None,
    busca: Annotated[str | None, Query(max_length=100)] = None,
) -> Response:
    _validar_periodo(de, ate)
    filtro = FiltroContas(situacao, de, ate, busca=(busca or "").strip() or None)
    conteudo = relatorio_service.contas_csv(db, vinculo.restaurante_id, filtro, tempo.hoje())
    return _csv(conteudo, f"contas_{situacao.value}_{_sufixo(de, ate)}.csv")
