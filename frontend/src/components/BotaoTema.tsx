import type { Tema } from '../hooks/useTema'
import { Icone } from './Icone'

export interface ControleTema {
  tema: Tema
  alternar: () => void
}

/** Mostra para onde vai mudar: no claro, oferece "Tema escuro" (lua); no escuro, "Tema claro" (sol). */
export function BotaoTema({ tema, alternar }: ControleTema) {
  const destino = tema === 'escuro' ? 'claro' : 'escuro'
  return (
    <button type="button" className="botao-tema" onClick={alternar}>
      <Icone nome={destino === 'escuro' ? 'lua' : 'sol'} tamanho={18} />
      Tema {destino}
    </button>
  )
}
