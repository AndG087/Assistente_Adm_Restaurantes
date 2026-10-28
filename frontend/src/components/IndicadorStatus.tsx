import type { StatusSistema } from '../hooks/useStatusSistema'
import { StatusBadge, type NivelStatus } from './StatusBadge'

/**
 * O que precisa da atenção de quem usa, em palavras do dia a dia; null quando está tudo funcionando.
 * Com tudo certo, o indicador fica discreto: detalhes técnicos só aparecem quando algo falha.
 */
function problema({ carregando, backend, ia }: StatusSistema): [NivelStatus, string] | null {
  if (carregando && !backend) return ['verificando', 'Verificando…']
  if (!backend) return ['erro', 'Sistema desconectado']
  if (backend.banco_de_dados !== 'ok') return ['erro', 'Banco de dados indisponível']
  if (carregando && !ia) return ['verificando', 'Verificando…']
  if (!ia) return ['alerta', 'IA sem resposta']
  if (!ia.ollama_disponivel) return ['alerta', 'IA desligada']
  if (!ia.modelo_disponivel) {
    return ['alerta', ia.modelo ? `Modelo de IA ${ia.modelo} não instalado` : 'Modelo de IA não instalado']
  }
  return null
}

export function IndicadorStatus({ status }: { status: StatusSistema }) {
  const aviso = problema(status)

  if (!aviso) {
    return (
      <span
        className="indicador-status"
        role="status"
        title={`Sistema conectado · IA: ${status.ia?.modelo ?? 'disponível'}`}
      >
        <span className="indicador-status__ponto" aria-hidden="true" />
        Tudo funcionando
      </span>
    )
  }

  return (
    <div className="indicador-status indicador-status--problema">
      <StatusBadge nivel={aviso[0]} descricao={aviso[1]} />
      <button type="button" className="botao botao--secundario" onClick={status.atualizar} disabled={status.carregando}>
        Verificar novamente
      </button>
    </div>
  )
}
