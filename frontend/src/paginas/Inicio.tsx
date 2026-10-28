import { useState } from 'react'
import { BarrasTotais } from '../components/BarrasTotais'
import { Icone, type NomeIcone } from '../components/Icone'
import { ProximasContas } from '../components/ProximasContas'
import { useArea } from '../contexto'
import { useCarregar } from '../hooks/useCarregar'
import type { Pagina } from '../hooks/useNavegacao'
import { buscarAlertas, resumoDespesas } from '../recursos/financeiro'
import { formatarData, formatarMoeda, mesDe } from '../utils/formato'

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
  const r = resumo.dados
  // Lida uma vez, ao abrir a tela: a saudação não precisa mudar a cada novo desenho.
  const [agora] = useState(() => new Date())

  return (
    <div className="inicio">
      <header className="cabecalho-pagina">
        <div>
          <p className="cabecalho-pagina__sobretitulo">{DATA_POR_EXTENSO.format(agora)}</p>
          <h2 className="cabecalho-pagina__titulo">{saudacao(agora.getHours())}!</h2>
          <p className="cabecalho-pagina__descricao">Veja como estão as contas do restaurante hoje.</p>
        </div>
        <div className="cabecalho-pagina__acoes">
          <button type="button" className="botao botao--secundario" onClick={() => irPara('contas')}>
            Ver contas a pagar
          </button>
          <button type="button" className="botao botao--primario" onClick={() => irPara('documentos')}>
            <Icone nome="enviar" tamanho={18} />
            Enviar nota ou boleto
          </button>
        </div>
      </header>

      <section className="inicio__secao" aria-labelledby="titulo-vencimentos">
        <h3 id="titulo-vencimentos" className="inicio__titulo-secao">
          Vencimentos
        </h3>
        {alertas.erro && (
          <p className="alerta alerta--erro" role="alert">
            {alertas.erro}
          </p>
        )}
        {a && (
          <div className="indicadores">
            <Indicador
              titulo="Vencidas"
              icone="alerta"
              nivel={a.vencidas.quantidade ? 'erro' : 'neutro'}
              quantidade={a.vencidas.quantidade}
              valor={a.vencidas.valor_total}
              onAbrir={() => irPara('contas')}
            />
            <Indicador
              titulo="Vencem hoje"
              icone="relogio"
              nivel={a.vencem_hoje.quantidade ? 'alerta' : 'neutro'}
              quantidade={a.vencem_hoje.quantidade}
              valor={a.vencem_hoje.valor_total}
              onAbrir={() => irPara('contas')}
            />
            <Indicador
              titulo={`Próximos ${a.dias} dias`}
              icone="contas"
              nivel="neutro"
              quantidade={a.proximos_dias.quantidade}
              valor={a.proximos_dias.valor_total}
              onAbrir={() => irPara('contas')}
            />
          </div>
        )}
      </section>

      <div className="inicio__colunas">
        <section className="cartao painel-despesas" aria-labelledby="titulo-despesas-mes">
          <header className="painel-despesas__cabecalho">
            <div>
              <h3 id="titulo-despesas-mes" className="inicio__titulo-secao">
                Despesas de {NOME_DO_MES.format(new Date(`${mes.de}T12:00:00`))}
              </h3>
              <p className="painel-despesas__periodo">
                Por categoria · {formatarData(mes.de)} a {formatarData(mes.ate)}
              </p>
            </div>
            {r && r.quantidade > 0 && (
              <div className="painel-despesas__total">
                <span className="painel-despesas__rotulo">Total do mês</span>
                <strong>{formatarMoeda(r.valor_total)}</strong>
                <span>
                  {r.quantidade} {r.quantidade === 1 ? 'despesa' : 'despesas'}
                </span>
              </div>
            )}
          </header>

          {resumo.erro && (
            <p className="alerta alerta--erro" role="alert">
              {resumo.erro}
            </p>
          )}
          {r &&
            (r.quantidade === 0 ? (
              <p className="vazio">Nenhuma despesa registrada neste mês.</p>
            ) : (
              <BarrasTotais
                rotulo="Despesas por categoria"
                total={r.valor_total}
                itens={r.por_categoria.map((c) => ({
                  chave: String(c.categoria?.id ?? 'sem'),
                  nome: c.categoria?.nome ?? 'Sem categoria',
                  valor: c.valor_total,
                }))}
              />
            ))}

          <footer className="painel-despesas__rodape">
            <button type="button" className="link" onClick={() => irPara('despesas')}>
              Ver todas as despesas
            </button>
          </footer>
        </section>

        <ProximasContas
          onPagamento={() => {
            // Pagar gera uma despesa: vencimentos e total do mês mudam.
            alertas.recarregar()
            resumo.recarregar()
          }}
          onVerTodas={() => irPara('contas')}
        />
      </div>
    </div>
  )
}

interface IndicadorProps {
  titulo: string
  icone: NomeIcone
  nivel: 'erro' | 'alerta' | 'neutro'
  quantidade: number
  valor: string
  onAbrir: () => void
}

/** Cartão de vencimento; o cartão inteiro leva às contas a pagar. */
function Indicador({ titulo, icone, nivel, quantidade, valor, onAbrir }: IndicadorProps) {
  return (
    <button type="button" className={`cartao indicador indicador--${nivel}`} onClick={onAbrir}>
      <span className="indicador__icone" aria-hidden="true">
        <Icone nome={icone} tamanho={22} />
      </span>
      <span className="indicador__titulo">{titulo}</span>
      <span className="indicador__valor">{formatarMoeda(valor)}</span>
      <span className="indicador__detalhe">
        {quantidade === 0 ? 'Nenhuma conta' : `${quantidade} ${quantidade === 1 ? 'conta' : 'contas'}`}
      </span>
    </button>
  )
}
