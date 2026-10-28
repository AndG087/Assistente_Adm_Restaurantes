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
}

/**
 * Barras horizontais de uma única série (uma só cor, sem legenda: o título diz o que é).
 * O valor fica escrito ao lado de cada barra, então nenhuma informação depende de passar o mouse.
 */
export function BarrasTotais({ rotulo, itens }: BarrasTotaisProps) {
  const maior = Math.max(...itens.map((i) => Number(i.valor)), 0)

  return (
    <ul className="barras" aria-label={rotulo}>
      {itens.map((item) => (
        <li key={item.chave} className="barras__item">
          <span className="barras__nome">
            {item.nome}
            {item.detalhe && <span className="barras__detalhe"> · {item.detalhe}</span>}
          </span>
          <span className="barras__valor">{formatarMoeda(item.valor)}</span>
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
