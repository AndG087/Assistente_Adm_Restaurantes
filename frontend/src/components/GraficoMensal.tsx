import type { TotalMes } from '../recursos/relatorios'
import { formatarMoeda } from '../utils/formato'

const COMPACTO = new Intl.NumberFormat('pt-BR', { notation: 'compact', maximumFractionDigits: 1 })

function plural(quantidade: number): string {
  return `${quantidade} ${quantidade === 1 ? 'lançamento' : 'lançamentos'}`
}

/** Escala "redonda" para o eixo: o menor 1; 1,5; 2; 2,5; 3; 4; 5; 6; 8 ou 10 × 10ⁿ que cobre o maior valor. */
function topoDaEscala(maior: number): number {
  if (maior <= 0) return 1
  const potencia = 10 ** Math.floor(Math.log10(maior))
  const passo = [1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10].find((m) => m * potencia >= maior) ?? 10
  return passo * potencia
}

interface GraficoMensalProps {
  meses: TotalMes[]
}

/**
 * Colunas de uma única série (despesas por mês). Cada coluna recebe foco pelo teclado e mostra
 * o valor ao passar o mouse ou focar; só o mês atual e o maior mês têm o valor escrito.
 * A tabela abaixo traz todos os valores sem depender de interação.
 */
export function GraficoMensal({ meses }: GraficoMensalProps) {
  const valores = meses.map((m) => Number(m.valor_total))
  const topo = topoDaEscala(Math.max(...valores))
  const indiceMaior = valores.indexOf(Math.max(...valores))
  const indiceAtual = meses.length - 1
  const marcas = [topo, topo / 2, 0]

  return (
    <figure className="grafico-mensal">
      <div className="grafico-mensal__plot">
        <div className="grafico-mensal__eixo" aria-hidden="true">
          {marcas.map((marca) => (
            <span key={marca} className="grafico-mensal__marca" style={{ bottom: `${(marca / topo) * 100}%` }}>
              {marca === 0 ? '0' : COMPACTO.format(marca)}
            </span>
          ))}
        </div>
        <div className="grafico-mensal__area" role="list" aria-label="Despesas por mês">
          {marcas.map((marca) => (
            <span
              key={marca}
              className="grafico-mensal__grade"
              style={{ bottom: `${(marca / topo) * 100}%` }}
              aria-hidden="true"
            />
          ))}
          {meses.map((m, i) => {
            const altura = (Number(m.valor_total) / topo) * 100
            const rotulado = Number(m.valor_total) > 0 && (i === indiceAtual || i === indiceMaior)
            return (
              <div
                key={`${m.ano}-${m.mes}`}
                className={`coluna${i === indiceAtual ? ' coluna--atual' : ''}`}
                role="listitem"
                tabIndex={0}
                aria-label={`${m.rotulo}: ${formatarMoeda(m.valor_total)} em ${plural(m.quantidade)}`}
              >
                <span className="coluna__trilho">
                  {rotulado && (
                    <span className="coluna__valor" style={{ bottom: `${altura}%` }} aria-hidden="true">
                      {COMPACTO.format(Number(m.valor_total))}
                    </span>
                  )}
                  <span className="coluna__barra" style={{ height: `${altura}%` }} />
                </span>
                <span className="coluna__rotulo" aria-hidden="true">
                  {m.rotulo.slice(0, 3)}
                </span>
                <span className="coluna__dica" role="tooltip" aria-hidden="true">
                  <strong>{formatarMoeda(m.valor_total)}</strong>
                  <span>
                    {m.rotulo} · {plural(m.quantidade)}
                  </span>
                </span>
              </div>
            )
          })}
        </div>
      </div>

      <details className="grafico-mensal__tabela">
        <summary>Ver os valores em tabela</summary>
        <table className="tabela">
          <thead>
            <tr>
              <th scope="col">Mês</th>
              <th scope="col">Lançamentos</th>
              <th scope="col" className="tabela__numero">
                Total
              </th>
            </tr>
          </thead>
          <tbody>
            {meses.map((m) => (
              <tr key={`${m.ano}-${m.mes}`}>
                <td data-rotulo="Mês">{m.rotulo}</td>
                <td data-rotulo="Lançamentos">{m.quantidade}</td>
                <td data-rotulo="Total" className="tabela__numero">
                  {formatarMoeda(m.valor_total)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </figure>
  )
}
