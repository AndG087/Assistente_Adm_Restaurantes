import { formatarMoeda } from '../utils/formato'

export interface ItemBarra {
  chave: string
  nome: string
  valor: string
  detalhe?: string
}

interface BarrasTotaisProps {
  rotulo: string
  itens: ItemBarra[]
  /**
   * Total calculado pelo backend (ex.: despesas do mês). Quando informado, cada item mostra a sua
   * participação nele ("28,5%"). O frontend só divide: nenhum total em dinheiro é somado aqui.
   */
  total?: string
}

const PERCENTUAL = new Intl.NumberFormat('pt-BR', { style: 'percent', maximumFractionDigits: 1 })

/**
 * Barras horizontais de uma única série (uma só cor, sem legenda: o título diz o que é).
 * O valor fica escrito ao lado de cada barra, então nenhuma informação depende de passar o mouse.
 */
export function BarrasTotais({ rotulo, itens, total }: BarrasTotaisProps) {
  const maior = Math.max(...itens.map((i) => Number(i.valor)), 0)
  const mostrarPercentual = total !== undefined
  const base = Number(total)

  return (
    <ul className={`barras${mostrarPercentual ? ' barras--percentual' : ''}`} aria-label={rotulo}>
      {itens.map((item) => (
        <li key={item.chave} className="barras__item">
          <span className="barras__nome">
            {item.nome}
            {item.detalhe && <span className="barras__detalhe"> · {item.detalhe}</span>}
          </span>
          <span className="barras__valor">{formatarMoeda(item.valor)}</span>
          {mostrarPercentual && (
            <span className="barras__percentual">{base > 0 ? PERCENTUAL.format(Number(item.valor) / base) : '—'}</span>
          )}
          <span className="barras__trilho" aria-hidden="true">
            <span
              className="barras__preenchimento"
              style={{ width: maior > 0 ? `${(Number(item.valor) / maior) * 100}%` : '0%' }}
            />
          </span>
        </li>
      ))}
    </ul>
  )
}
