import type { Usuario } from '../api'
import type { StatusSistema } from '../hooks/useStatusSistema'
import { BotaoTema, type ControleTema } from './BotaoTema'
import { IndicadorStatus } from './IndicadorStatus'
import { Logo } from './Logo'

interface CabecalhoProps {
  status: StatusSistema
  tema: ControleTema
  usuario: Usuario | null
  onSair: () => void
}

/** Topo das telas sem barra lateral: login e cadastro do primeiro restaurante. */
export function Cabecalho({ status, tema, usuario, onSair }: CabecalhoProps) {
  return (
    <header className="cabecalho">
      <div className="cabecalho__marca">
        <Logo />
        <div>
          <h1 className="cabecalho__titulo">Caderninho</h1>
          <p className="cabecalho__subtitulo">As contas do restaurante em dia</p>
        </div>
      </div>

      <div className="cabecalho__status">
        <IndicadorStatus status={status} />
        <BotaoTema {...tema} />
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

export function Rodape() {
  return <footer className="rodape">Caderninho · Cada restaurante enxerga só os próprios dados</footer>
}
