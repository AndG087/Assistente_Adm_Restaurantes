import type { Restaurante, Usuario } from '../api'
import { PAGINAS, type Pagina } from '../hooks/useNavegacao'
import type { StatusSistema } from '../hooks/useStatusSistema'
import { formatarDocumento } from '../utils/formato'
import { BotaoTema, type ControleTema } from './BotaoTema'
import { Icone } from './Icone'
import { IndicadorStatus } from './IndicadorStatus'
import { Logo } from './Logo'

// Ordem de uso no dia a dia do restaurante, não ordem alfabética.
const GRUPOS: { titulo: string; paginas: Pagina[] }[] = [
  { titulo: 'Dia a dia', paginas: ['inicio', 'documentos', 'contas', 'despesas', 'assistente'] },
  { titulo: 'Acompanhar', paginas: ['relatorios'] },
  { titulo: 'Cadastros', paginas: ['fornecedores', 'categorias', 'equipe'] },
]

const PAPEIS = { proprietario: 'Proprietário', membro: 'Membro' } as const

function iniciais(nome: string): string {
  const partes = nome.trim().split(/\s+/)
  return ((partes[0]?.[0] ?? '') + (partes.length > 1 ? partes[partes.length - 1][0] : '')).toUpperCase()
}

interface MenuLateralProps {
  pagina: Pagina
  restaurantes: Restaurante[]
  restaurante: Restaurante
  onSelecionarRestaurante: (id: number) => void
  onNovoRestaurante: () => void
  usuario: Usuario
  status: StatusSistema
  tema: ControleTema
  onSair: () => void
  /** No celular o menu é uma gaveta: aberto/fechado. Na tela grande ele está sempre visível. */
  aberto: boolean
  onFechar: () => void
}

export function MenuLateral({
  pagina,
  restaurantes,
  restaurante,
  onSelecionarRestaurante,
  onNovoRestaurante,
  usuario,
  status,
  tema,
  onSair,
  aberto,
  onFechar,
}: MenuLateralProps) {
  return (
    <aside id="menu-lateral" className={`menu-lateral${aberto ? ' menu-lateral--aberto' : ''}`} aria-label="Menu">
      <div className="menu-lateral__marca">
        <Logo tamanho={36} />
        <span className="menu-lateral__nome">Caderninho</span>
        <button type="button" className="menu-lateral__fechar" aria-label="Fechar menu" onClick={onFechar}>
          <Icone nome="fechar" />
        </button>
      </div>

      <section className="menu-lateral__restaurante" aria-label="Restaurante selecionado">
        <label className="menu-lateral__rotulo" htmlFor="restaurante-atual">
          Restaurante
        </label>
        <select
          id="restaurante-atual"
          className="campo__entrada"
          value={restaurante.id}
          onChange={(e) => onSelecionarRestaurante(Number(e.target.value))}
        >
          {restaurantes.map((r) => (
            <option key={r.id} value={r.id}>
              {r.nome}
            </option>
          ))}
        </select>
        <p className="menu-lateral__detalhe">
          <span>{PAPEIS[restaurante.papel]}</span>
          {restaurante.cnpj && (
            <>
              {' · '}
              <span>{formatarDocumento(restaurante.cnpj)}</span>
            </>
          )}
        </p>
        <button type="button" className="link menu-lateral__novo" onClick={onNovoRestaurante}>
          + Novo restaurante
        </button>
      </section>

      {/* O gesto mais comum do dia: mandar a nota assim que ela chega. */}
      <a href="#/documentos" className="botao botao--primario menu-lateral__acao" onClick={onFechar}>
        <Icone nome="enviar" />
        Enviar nota ou boleto
      </a>

      <nav className="menu-lateral__nav" aria-label="Seções">
        {GRUPOS.map((grupo) => (
          <div key={grupo.titulo} className="menu-lateral__grupo">
            <p className="menu-lateral__grupo-titulo">{grupo.titulo}</p>
            <ul>
              {grupo.paginas.map((chave) => (
                <li key={chave}>
                  <a
                    href={`#/${chave}`}
                    className="menu-lateral__item"
                    aria-current={pagina === chave ? 'page' : undefined}
                    onClick={onFechar}
                  >
                    <Icone nome={chave} />
                    <span>{PAGINAS[chave]}</span>
                  </a>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </nav>

      <div className="menu-lateral__rodape">
        <div className="menu-lateral__ajustes">
          <IndicadorStatus status={status} />
          <BotaoTema {...tema} />
        </div>
        <div className="menu-lateral__usuario">
          <span className="avatar" aria-hidden="true">
            {iniciais(usuario.nome)}
          </span>
          <span className="menu-lateral__usuario-nome" title={usuario.email}>
            {usuario.nome}
          </span>
          <button type="button" className="botao botao--secundario" onClick={onSair}>
            Sair
          </button>
        </div>
      </div>
    </aside>
  )
}
