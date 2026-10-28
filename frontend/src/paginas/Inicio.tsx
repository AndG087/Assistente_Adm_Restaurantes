import { BarrasTotais } from '../components/BarrasTotais'
import { useArea } from '../contexto'
import { useCarregar } from '../hooks/useCarregar'
import type { Pagina } from '../hooks/useNavegacao'
import { buscarAlertas, resumoDespesas } from '../recursos/financeiro'
import { formatarMoeda, mesDe } from '../utils/formato'

interface InicioProps {
  irPara: (pagina: Pagina) => void
}

const NOME_DO_MES = new Intl.DateTimeFormat('pt-BR', { month: 'long', year: 'numeric' })
const DATA_POR_EXTENSO = new Intl.DateTimeFormat('pt-BR', { weekday: 'long', day: 'numeric', month: 'long' })

function saudacao(hora: number): string {
  if (hora < 12) return 'Bom dia'
  return hora < 18 ? 'Boa tarde' : 'Boa noite'
}

/** Visão geral com dados reais: alertas de vencimento e despesas do mês, calculados pelo backend. */
export function Inicio({ irPara }: InicioProps) {
  const { restaurante } = useArea()
  const mes = mesDe()
  const alertas = useCarregar(`alertas-${restaurante.id}`, () => buscarAlertas(restaurante.id))
  const resumo = useCarregar(`resumo-${restaurante.id}-${mes.de}`, () =>
    resumoDespesas(restaurante.id, mes.de, mes.ate),
  )

  const a = alertas.dados
  const agora = new Date()

  return (
    <div className="inicio">
      <header className="inicio__boas-vindas">
        <h2 className="inicio__saudacao">{saudacao(agora.getHours())}!</h2>
        <p>Veja como estão as contas do restaurante hoje, {DATA_POR_EXTENSO.format(agora)}.</p>
      </header>
      <section aria-labelledby="titulo-vencimentos">
        <h2 id="titulo-vencimentos" className="inicio__titulo">
          Vencimentos
        </h2>
        {alertas.erro && (
          <p className="alerta alerta--erro" role="alert">
            {alertas.erro}
          </p>
        )}
        {a && (
          <div className="indicadores">
            <Indicador
              titulo="Vencidas"
              nivel={a.vencidas.quantidade ? 'erro' : 'neutro'}
              quantidade={a.vencidas.quantidade}
              valor={a.vencidas.valor_total}
            />
            <Indicador
              titulo="Vencem hoje"
              nivel={a.vencem_hoje.quantidade ? 'alerta' : 'neutro'}
              quantidade={a.vencem_hoje.quantidade}
              valor={a.vencem_hoje.valor_total}
            />
            <Indicador
              titulo={`Próximos ${a.dias} dias`}
              nivel="neutro"
              quantidade={a.proximos_dias.quantidade}
              valor={a.proximos_dias.valor_total}
            />
          </div>
        )}
        <button type="button" className="link" onClick={() => irPara('contas')}>
          Ver contas a pagar
        </button>
      </section>

      <section className="cartao inicio__despesas" aria-labelledby="titulo-despesas-mes">
        <h2 id="titulo-despesas-mes" className="inicio__titulo">
          Despesas de {NOME_DO_MES.format(new Date(`${mes.de}T12:00:00`))}
        </h2>
        {resumo.erro && (
          <p className="alerta alerta--erro" role="alert">
            {resumo.erro}
          </p>
        )}
        {resumo.dados &&
          (resumo.dados.quantidade === 0 ? (
            <p className="vazio">Nenhuma despesa registrada neste mês.</p>
          ) : (
            <>
              <p className="inicio__total">
                {formatarMoeda(resumo.dados.valor_total)}
                <span>
                  {' '}
                  em {resumo.dados.quantidade} {resumo.dados.quantidade === 1 ? 'despesa' : 'despesas'}
                </span>
              </p>
              <BarrasTotais
                rotulo="Despesas por categoria"
                itens={resumo.dados.por_categoria.map((c) => ({
                  chave: String(c.categoria?.id ?? 'sem'),
                  nome: c.categoria?.nome ?? 'Sem categoria',
                  valor: c.valor_total,
                }))}
              />
            </>
          ))}
        <button type="button" className="link" onClick={() => irPara('despesas')}>
          Ver despesas
        </button>
      </section>
    </div>
  )
}

interface IndicadorProps {
  titulo: string
  nivel: 'erro' | 'alerta' | 'neutro'
  quantidade: number
  valor: string
}

function Indicador({ titulo, nivel, quantidade, valor }: IndicadorProps) {
  return (
    <div className={`cartao indicador indicador--${nivel}`}>
      <span className="indicador__titulo">{titulo}</span>
      <span className="indicador__valor">{formatarMoeda(valor)}</span>
      <span className="indicador__detalhe">
        {quantidade} {quantidade === 1 ? 'conta' : 'contas'}
      </span>
    </div>
  )
}
