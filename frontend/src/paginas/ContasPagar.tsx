import { useState } from 'react'
import { FormLancamento } from '../components/FormLancamento'
import { Paginacao } from '../components/Paginacao'
import { useArea } from '../contexto'
import { useCarregar } from '../hooks/useCarregar'
import {
  desfazerPagamento,
  excluirConta,
  listarContas,
  pagarConta,
  salvarConta,
  type ContaPagar,
  type FiltroSituacao,
  type SituacaoConta,
} from '../recursos/financeiro'
import { formatarData, formatarMoeda, hojeIso } from '../utils/formato'

const LIMITE = 50

const ABAS: Record<FiltroSituacao, string> = {
  pendentes: 'Pendentes',
  vencidas: 'Vencidas',
  pagas: 'Pagas',
  todas: 'Todas',
}

const SITUACOES: Record<SituacaoConta, string> = {
  vencida: 'Vencida',
  vence_hoje: 'Vence hoje',
  a_vencer: 'A vencer',
  paga: 'Paga',
}

type Edicao = { modo: 'nova' } | { modo: 'editar'; conta: ContaPagar } | null

export function ContasPagar() {
  const { restaurante, mensagemDeErro } = useArea()
  const [situacao, setSituacao] = useState<FiltroSituacao>('pendentes')
  const [busca, setBusca] = useState('')
  const [deslocamento, setDeslocamento] = useState(0)
  const [edicao, setEdicao] = useState<Edicao>(null)
  // Conta cujo pagamento está sendo confirmado, com a data escolhida.
  const [pagando, setPagando] = useState<{ conta: ContaPagar; data: string } | null>(null)
  const [erroAcao, setErroAcao] = useState<string | null>(null)

  const filtros = { situacao, busca: busca.trim(), limite: LIMITE, deslocamento }
  const lista = useCarregar(`${restaurante.id}|${JSON.stringify(filtros)}`, () =>
    listarContas(restaurante.id, filtros),
  )

  async function executar(acao: () => Promise<unknown>) {
    setErroAcao(null)
    try {
      await acao()
      lista.recarregar()
    } catch (e) {
      setErroAcao(mensagemDeErro(e))
    }
  }

  function confirmarPagamento() {
    if (!pagando) return
    const { conta, data } = pagando
    setPagando(null)
    void executar(() => pagarConta(restaurante.id, conta.id, data))
  }

  if (edicao) {
    const conta = edicao.modo === 'editar' ? edicao.conta : null
    return (
      <FormLancamento
        titulo={conta ? 'Editar conta' : 'Nova conta a pagar'}
        rotuloData="Vencimento"
        inicial={conta ? { ...conta, data: conta.data_vencimento } : undefined}
        onCancelar={() => setEdicao(null)}
        onSalvar={async (dados, data) => {
          await salvarConta(restaurante.id, conta?.id ?? null, { ...dados, data_vencimento: data })
          setEdicao(null)
          lista.recarregar()
        }}
      />
    )
  }

  return (
    <section className="pagina-secao" aria-labelledby="titulo-contas">
      <header className="pagina-secao__cabecalho">
        <h2 id="titulo-contas">Contas a pagar</h2>
        <button type="button" className="botao botao--primario" onClick={() => setEdicao({ modo: 'nova' })}>
          Nova conta
        </button>
      </header>

      <div className="cartao filtros">
        <div className="segmentos" role="group" aria-label="Situação">
          {(Object.keys(ABAS) as FiltroSituacao[]).map((chave) => (
            <button
              key={chave}
              type="button"
              className="segmentos__item"
              aria-pressed={situacao === chave}
              onClick={() => {
                setSituacao(chave)
                setDeslocamento(0)
              }}
            >
              {ABAS[chave]}
            </button>
          ))}
        </div>
        <label className="campo">
          <span className="campo__rotulo">Buscar</span>
          <input
            className="campo__entrada"
            type="search"
            value={busca}
            onChange={(e) => {
              setBusca(e.target.value)
              setDeslocamento(0)
            }}
            placeholder="Descrição ou nº do documento"
            maxLength={100}
          />
        </label>
      </div>

      {pagando && (
        <div className="cartao confirmacao" role="dialog" aria-label="Confirmar pagamento">
          <p>
            Registrar o pagamento de <strong>{pagando.conta.descricao}</strong> (
            {formatarMoeda(pagando.conta.valor)})? Uma despesa será criada automaticamente.
          </p>
          <label className="campo campo--em-linha">
            <span className="campo__rotulo">Data do pagamento</span>
            <input
              className="campo__entrada"
              type="date"
              value={pagando.data}
              max={hojeIso()}
              onChange={(e) => setPagando({ ...pagando, data: e.target.value })}
            />
          </label>
          <div className="formulario__acoes">
            <button type="button" className="botao botao--secundario" onClick={() => setPagando(null)}>
              Cancelar
            </button>
            <button type="button" className="botao botao--primario" onClick={confirmarPagamento}>
              Confirmar pagamento
            </button>
          </div>
        </div>
      )}

      {(lista.erro || erroAcao) && (
        <p className="alerta alerta--erro" role="alert">
          {erroAcao ?? lista.erro}
        </p>
      )}

      {lista.dados && (
        <div className="cartao tabela-container" aria-busy={lista.carregando}>
          <p className="tabela-resumo">
            {lista.dados.total} {lista.dados.total === 1 ? 'conta' : 'contas'} · Total{' '}
            <strong>{formatarMoeda(lista.dados.valor_total)}</strong>
          </p>
          {lista.dados.itens.length === 0 ? (
            <p className="vazio">Nenhuma conta nesta situação.</p>
          ) : (
            <table className="tabela">
              <thead>
                <tr>
                  <th scope="col">Vencimento</th>
                  <th scope="col">Descrição</th>
                  <th scope="col">Fornecedor</th>
                  <th scope="col">Situação</th>
                  <th scope="col" className="tabela__numero">
                    Valor
                  </th>
                  <th scope="col">
                    <span className="visualmente-oculto">Ações</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {lista.dados.itens.map((c) => (
                  <tr key={c.id}>
                    <td data-rotulo="Vencimento">{formatarData(c.data_vencimento)}</td>
                    <td data-rotulo="Descrição">
                      {c.descricao}
                      {c.categoria && <span className="tabela__detalhe">{c.categoria.nome}</span>}
                    </td>
                    <td data-rotulo="Fornecedor">{c.fornecedor?.nome ?? <span className="suave">—</span>}</td>
                    <td data-rotulo="Situação">
                      <span className={`situacao situacao--${c.situacao}`}>{SITUACOES[c.situacao]}</span>
                      {c.data_pagamento && (
                        <span className="tabela__detalhe">em {formatarData(c.data_pagamento)}</span>
                      )}
                    </td>
                    <td data-rotulo="Valor" className="tabela__numero">
                      {formatarMoeda(c.valor)}
                    </td>
                    <td className="tabela__acoes">
                      {c.situacao === 'paga' ? (
                        <button
                          type="button"
                          className="link"
                          aria-label={`Desfazer pagamento de ${c.descricao}`}
                          onClick={() => {
                            if (window.confirm(`Desfazer o pagamento de "${c.descricao}"? A despesa gerada será removida.`))
                              void executar(() => desfazerPagamento(restaurante.id, c.id))
                          }}
                        >
                          Desfazer pagamento
                        </button>
                      ) : (
                        <>
                          <button
                            type="button"
                            className="link"
                            aria-label={`Pagar ${c.descricao}`}
                            onClick={() => setPagando({ conta: c, data: hojeIso() })}
                          >
                            Pagar
                          </button>
                          <button
                            type="button"
                            className="link"
                            aria-label={`Editar ${c.descricao}`}
                            onClick={() => setEdicao({ modo: 'editar', conta: c })}
                          >
                            Editar
                          </button>
                          <button
                            type="button"
                            className="link link--perigo"
                            aria-label={`Excluir ${c.descricao}`}
                            onClick={() => {
                              if (window.confirm(`Excluir a conta "${c.descricao}"?`))
                                void executar(() => excluirConta(restaurante.id, c.id))
                            }}
                          >
                            Excluir
                          </button>
                        </>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <Paginacao deslocamento={deslocamento} limite={LIMITE} total={lista.dados.total} onMudar={setDeslocamento} />
        </div>
      )}
    </section>
  )
}
