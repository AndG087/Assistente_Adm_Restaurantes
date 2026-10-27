import type { Usuario } from '../api'
import type { StatusSistema } from '../hooks/useStatusSistema'
import { StatusBadge, type NivelStatus } from './StatusBadge'

interface CabecalhoProps {
  status: StatusSistema
  usuario: Usuario | null
  onSair: () => void
}

function statusBackend({ carregando, backend }: StatusSistema): [NivelStatus, string] {
  if (carregando && !backend) return ['verificando', 'Verificando…']
  if (!backend) return ['erro', 'Desconectado']
  if (backend.banco_de_dados !== 'ok') return ['alerta', 'Conectado, banco indisponível']
  return ['ok', 'Conectado']
}

function statusIA({ carregando, ia }: StatusSistema): [NivelStatus, string] {
  if (carregando && !ia) return ['verificando', 'Verificando…']
  if (!ia) return ['erro', 'Sem informação']
  if (!ia.ollama_disponivel) return ['erro', 'Ollama desligado']
  if (!ia.modelo_disponivel) return ['alerta', `Modelo ${ia.modelo} não instalado`]
  return ['ok', ia.modelo]
}

export function Cabecalho({ status, usuario, onSair }: CabecalhoProps) {
  const [nivelBackend, descricaoBackend] = statusBackend(status)
  const [nivelIA, descricaoIA] = statusIA(status)

  return (
    <header className="cabecalho">
      <div className="cabecalho__marca">
        <span className="cabecalho__logo" aria-hidden="true">RA</span>
        <div>
          <h1 className="cabecalho__titulo">Restaurante Admin AI</h1>
          <p className="cabecalho__subtitulo">Assistente administrativo para restaurantes</p>
        </div>
      </div>

      <div className="cabecalho__status">
        <StatusBadge rotulo="Backend" nivel={nivelBackend} descricao={descricaoBackend} />
        <StatusBadge rotulo="IA local" nivel={nivelIA} descricao={descricaoIA} />
        <button
          type="button"
          className="botao botao--secundario"
          onClick={status.atualizar}
          disabled={status.carregando}
        >
          Verificar novamente
        </button>
      </div>

      {usuario && (
        <div className="cabecalho__usuario">
          <span className="cabecalho__nome" title={usuario.email}>
            {usuario.nome}
          </span>
          <button type="button" className="botao botao--secundario" onClick={onSair}>
            Sair
          </button>
        </div>
      )}
    </header>
  )
}
