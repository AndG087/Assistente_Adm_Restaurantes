from fastapi import APIRouter, status

from app.api.deps import DbSession, UsuarioAtual, VinculoRestaurante
from app.models import MembroRestaurante
from app.schemas.restaurante import RestauranteCreate, RestauranteResponse
from app.services import restaurante_service

router = APIRouter(prefix="/restaurantes", tags=["Restaurantes"])


def _resposta(vinculo: MembroRestaurante) -> RestauranteResponse:
    restaurante = vinculo.restaurante
    return RestauranteResponse(id=restaurante.id, nome=restaurante.nome, cnpj=restaurante.cnpj, papel=vinculo.papel)


@router.get("", response_model=list[RestauranteResponse])
def listar(db: DbSession, usuario: UsuarioAtual) -> list[RestauranteResponse]:
    """Somente os restaurantes dos quais o usuário logado é membro."""
    return [_resposta(v) for v in restaurante_service.listar_do_usuario(db, usuario)]


@router.post("", response_model=RestauranteResponse, status_code=status.HTTP_201_CREATED)
def criar(dados: RestauranteCreate, db: DbSession, usuario: UsuarioAtual) -> RestauranteResponse:
    return _resposta(restaurante_service.criar(db, usuario, dados.nome, dados.cnpj))


@router.get("/{restaurante_id}", response_model=RestauranteResponse)
def obter(vinculo: VinculoRestaurante) -> RestauranteResponse:
    return _resposta(vinculo)
