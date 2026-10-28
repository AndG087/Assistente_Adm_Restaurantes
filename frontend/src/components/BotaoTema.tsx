import type { Tema } from '../hooks/useTema'
import { Icone } from './Icone'

export interface ControleTema {
  tema: Tema
  alternar: () => void
}

/**
 * Mostra para onde vai mudar: no claro, oferece "Tema escuro" (lua); no escuro, "Tema claro" (sol).
 * Compacto: só o ícone, com o mesmo nome para leitores de tela e na dica do mouse.
 */
export function BotaoTema({ tema, alternar, compacto = false }: ControleTema & { compacto?: boolean }) {
  const destino = tema === 'escuro' ? 'claro' : 'escuro'
  const rotulo = `Tema ${destino}`
  return (
    <button
      type="button"
      className={`botao-tema${compacto ? ' botao-tema--compacto' : ''}`}
      onClick={alternar}
      aria-label={compacto ? rotulo : undefined}
      title={compacto ? rotulo : undefined}
    >
      <Icone nome={destino === 'escuro' ? 'lua' : 'sol'} tamanho={18} />
      {!compacto && rotulo}
    </button>
  )
}
