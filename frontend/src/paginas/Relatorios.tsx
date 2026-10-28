import { useState } from 'react'
import { BarrasTotais } from '../components/BarrasTotais'
import { GraficoMensal } from '../components/GraficoMensal'
import { useArea } from '../contexto'
import { useCarregar } from '../hooks/useCarregar'
import { resumoDespesas } from '../recursos/financeiro'
import { evolucaoMensal, totaisPorFornecedor, urlCsvContas, urlCsvDespesas } from '../recursos/relatorios'
import { formatarData, formatarMoeda, mesDe } from '../utils/formato'

function lancamentos(quantidade: number): string {
  return `${quantidade} ${quantidade === 1 ? 'lançamento' : 'lançamentos'}`
}

export function Relatorios() {
  const { restaurante } = useArea()
  const [periodo, setPeriodo] = useState(mesDe)
  const periodoValido = Boolean(periodo.de && periodo.ate && periodo.de <= periodo.ate)
  const chave = `${restaurante.id}|${periodo.de}|${periodo.ate}`

  const mensal = useCarregar(`mensal-${restaurante.id}`, () => evolucaoMensal(restaurante.id, 12))
  const categorias = useCarregar(`cat-${chave}`, () =>
    periodoValido ? resumoDespesas(restaurante.id, periodo.de, periodo.ate) : Promise.resolve(null),
  )
  const fornecedores = useCarregar(`forn-${chave}`, () =>
    periodoValido ? totaisPorFornecedor(restaurante.id, periodo.de, periodo.ate) : Promise.resolve(null),
  )

  const resumo = categorias.dados
  const erro = mensal.erro ?? categorias.erro ?? fornecedores.erro

  return (
    <section className="pagina-secao" aria-labelledby="titulo-relatorios">
      <header className="pagina-secao__cabecalho">
        <h2 id="titulo-relatorios">Relatórios</h2>
      </header>

      {/* Filtros numa única linha, acima de tudo o que eles afetam. */}
      <div className="cartao filtros">
        <label className="campo">
          <span className="campo__rotulo">De</span>
          <input
            className="campo__entrada"
            type="date"
            value={periodo.de}
            onChange={(e) => setPeriodo({ ...periodo, de: e.target.value })}
          />
        </label>
        <label className="campo">
          <span className="campo__rotulo">Até</span>
          <input
            className="campo__entrada"
            type="date"
            value={periodo.ate}
            onChange={(e) => setPeriodo({ ...periodo, ate: e.target.value })}
          />
        </label>
        <div className="filtros__acoes">
          {periodoValido ? (
            <>
              <a className="botao botao--secundario" href={urlCsvDespesas(restaurante.id, periodo.de, periodo.ate)} download>
                Exportar despesas (CSV)
              </a>
              <a
                className="botao botao--secundario"
                href={urlCsvContas(restaurante.id, 'todas', periodo.de, periodo.ate)}
                download
                title="Contas com vencimento no período"
              >
                Exportar contas (CSV)
              </a>
            </>
          ) : (
            <button type="button" className="botao botao--secundario" disabled>
              Exportar (CSV)
            </button>
          )}
        </div>
      </div>

      {!periodoValido && (
        <p className="alerta alerta--erro" role="alert">
          Escolha um período válido (a data inicial não pode ser posterior à final).
        </p>
      )}
      {erro && (
        <p className="alerta alerta--erro" role="alert">
          {erro}
        </p>
      )}

      {resumo && periodoValido && (
        <div className="indicadores" aria-label="Totais do período">
          <div className="cartao indicador">
            <span className="indicador__titulo">Despesas no período</span>
            <span className="indicador__valor">{formatarMoeda(resumo.valor_total)}</span>
            <span className="indicador__detalhe">
              {formatarData(periodo.de)} a {formatarData(periodo.ate)}
            </span>
          </div>
          <div className="cartao indicador">
            <span className="indicador__titulo">Lançamentos</span>
            <span className="indicador__valor">{resumo.quantidade}</span>
            <span className="indicador__detalhe">despesas registradas</span>
          </div>
          {mensal.dados && (
            <div className="cartao indicador">
              <span className="indicador__titulo">Média mensal</span>
              <span className="indicador__valor">{formatarMoeda(mensal.dados.media_mensal)}</span>
              <span className="indicador__detalhe">últimos 11 meses completos</span>
            </div>
          )}
        </div>
      )}

      {mensal.dados && (
        <section className="cartao relatorio-bloco" aria-labelledby="titulo-mensal">
          <h3 id="titulo-mensal" className="relatorio-bloco__titulo">
            Despesas por mês
          </h3>
          <p className="relatorio-bloco__subtitulo">Últimos 12 meses, incluindo o mês atual (em andamento)</p>
          <GraficoMensal meses={mensal.dados.meses} />
        </section>
      )}

      {periodoValido && (
        <div className="relatorio-colunas">
          <section className="cartao relatorio-bloco" aria-labelledby="titulo-por-categoria" aria-busy={categorias.carregando}>
            <h3 id="titulo-por-categoria" className="relatorio-bloco__titulo">
              Por categoria
            </h3>
            {resumo && resumo.por_categoria.length === 0 && <p className="vazio">Nenhuma despesa no período.</p>}
            {resumo && resumo.por_categoria.length > 0 && (
              <BarrasTotais
                rotulo="Despesas por categoria"
                itens={resumo.por_categoria.map((c) => ({
                  chave: String(c.categoria?.id ?? 'sem'),
                  nome: c.categoria?.nome ?? 'Sem categoria',
                  valor: c.valor_total,
                  detalhe: lancamentos(c.quantidade),
                }))}
              />
            )}
          </section>

          <section className="cartao relatorio-bloco" aria-labelledby="titulo-por-fornecedor" aria-busy={fornecedores.carregando}>
            <h3 id="titulo-por-fornecedor" className="relatorio-bloco__titulo">
              Por fornecedor
            </h3>
            {fornecedores.dados && fornecedores.dados.length === 0 && (
              <p className="vazio">Nenhuma despesa no período.</p>
            )}
            {fornecedores.dados && fornecedores.dados.length > 0 && (
              <BarrasTotais
                rotulo="Despesas por fornecedor"
                itens={fornecedores.dados.map((f) => ({
                  chave: String(f.fornecedor?.id ?? 'sem'),
                  nome: f.fornecedor?.nome ?? 'Sem fornecedor',
                  valor: f.valor_total,
                  detalhe: lancamentos(f.quantidade),
                }))}
              />
            )}
          </section>
        </div>
      )}
    </section>
  )
}
