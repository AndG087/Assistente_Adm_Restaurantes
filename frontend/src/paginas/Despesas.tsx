import { useState } from 'react'
import { FormLancamento } from '../components/FormLancamento'
import { Paginacao } from '../components/Paginacao'
import { useArea } from '../contexto'
import { useCarregar } from '../hooks/useCarregar'
import { listarCategorias } from '../recursos/cadastros'
import { excluirDespesa, listarDespesas, salvarDespesa, type Despesa } from '../recursos/financeiro'
import { formatarData, formatarMoeda, mesDe } from '../utils/formato'

const LIMITE = 50
const SEM_CATEGORIA = 'sem'

type Edicao = { modo: 'nova' } | { modo: 'editar'; despesa: Despesa } | null

export function Despesas() {
  const { restaurante, mensagemDeErro } = useArea()
  const [periodo, setPeriodo] = useState(mesDe)
  const [categoria, setCategoria] = useState('')
  const [busca, setBusca] = useState('')
  const [deslocamento, setDeslocamento] = useState(0)
  const [edicao, setEdicao] = useState<Edicao>(null)
  const [erroAcao, setErroAcao] = useState<string | null>(null)

  const filtros = {
    ...periodo,
    categoria_id: categoria && categoria !== SEM_CATEGORIA ? Number(categoria) : null,
    sem_categoria: categoria === SEM_CATEGORIA,
    busca: busca.trim(),
    limite: LIMITE,
    deslocamento,
  }
  const lista = useCarregar(`${restaurante.id}|${JSON.stringify(filtros)}`, () =>
    listarDespesas(restaurante.id, filtros),
  )
  const categorias = useCarregar(`categorias-${restaurante.id}`, () => listarCategorias(restaurante.id, true))

  // Qualquer mudança de filtro volta para a primeira página.
  function filtrar(aplicar: () => void) {
    aplicar()
    setDeslocamento(0)
  }

  async function excluir(despesa: Despesa) {
    if (!window.confirm(`Excluir a despesa "${despesa.descricao}"?`)) return
    setErroAcao(null)
    try {
      await excluirDespesa(restaurante.id, despesa.id)
      lista.recarregar()
    } catch (e) {
      setErroAcao(mensagemDeErro(e))
    }
  }

  if (edicao) {
    const despesa = edicao.modo === 'editar' ? edicao.despesa : null
    return (
      <FormLancamento
        titulo={despesa ? 'Editar despesa' : 'Nova despesa'}
        rotuloData="Data da despesa"
        inicial={despesa ?? undefined}
        onCancelar={() => setEdicao(null)}
        onSalvar={async (dados, data) => {
          await salvarDespesa(restaurante.id, despesa?.id ?? null, { ...dados, data })
          setEdicao(null)
          lista.recarregar()
        }}
      />
    )
  }

  return (
    <section className="pagina-secao" aria-labelledby="titulo-despesas">
      <header className="pagina-secao__cabecalho">
        <h2 id="titulo-despesas">Despesas</h2>
        <button type="button" className="botao botao--primario" onClick={() => setEdicao({ modo: 'nova' })}>
          Nova despesa
        </button>
      </header>

      <div className="cartao filtros">
        <label className="campo">
          <span className="campo__rotulo">De</span>
          <input
            className="campo__entrada"
            type="date"
            value={periodo.de}
            onChange={(e) => filtrar(() => setPeriodo({ ...periodo, de: e.target.value }))}
          />
        </label>
        <label className="campo">
          <span className="campo__rotulo">Até</span>
          <input
            className="campo__entrada"
            type="date"
            value={periodo.ate}
            onChange={(e) => filtrar(() => setPeriodo({ ...periodo, ate: e.target.value }))}
          />
        </label>
        <label className="campo">
          <span className="campo__rotulo">Categoria</span>
          <select
            className="campo__entrada"
            value={categoria}
            onChange={(e) => filtrar(() => setCategoria(e.target.value))}
          >
            <option value="">Todas</option>
            <option value={SEM_CATEGORIA}>Sem categoria</option>
            {categorias.dados?.map((c) => (
              <option key={c.id} value={c.id}>
                {c.nome}
                {c.ativo ? '' : ' (inativa)'}
              </option>
            ))}
          </select>
        </label>
        <label className="campo">
          <span className="campo__rotulo">Buscar</span>
          <input
            className="campo__entrada"
            type="search"
            value={busca}
            onChange={(e) => filtrar(() => setBusca(e.target.value))}
            placeholder="Descrição ou nº do documento"
            maxLength={100}
          />
        </label>
      </div>

      {(lista.erro || erroAcao) && (
        <p className="alerta alerta--erro" role="alert">
          {erroAcao ?? lista.erro}
        </p>
      )}

      {lista.dados && (
        <div className="cartao tabela-container" aria-busy={lista.carregando}>
          <p className="tabela-resumo">
            {lista.dados.total} {lista.dados.total === 1 ? 'despesa' : 'despesas'} · Total{' '}
            <strong>{formatarMoeda(lista.dados.valor_total)}</strong>
          </p>
          {lista.dados.itens.length === 0 ? (
            <p className="vazio">Nenhuma despesa encontrada com estes filtros.</p>
          ) : (
            <table className="tabela">
              <thead>
                <tr>
                  <th scope="col">Data</th>
                  <th scope="col">Descrição</th>
                  <th scope="col">Categoria</th>
                  <th scope="col">Fornecedor</th>
                  <th scope="col" className="tabela__numero">
                    Valor
                  </th>
                  <th scope="col">
                    <span className="visualmente-oculto">Ações</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {lista.dados.itens.map((d) => (
                  <tr key={d.id}>
                    <td data-rotulo="Data">{formatarData(d.data)}</td>
                    <td data-rotulo="Descrição">
                      {d.descricao}
                      {d.numero_documento && <span className="tabela__detalhe">{d.numero_documento}</span>}
                    </td>
                    <td data-rotulo="Categoria">{d.categoria?.nome ?? <span className="suave">Sem categoria</span>}</td>
                    <td data-rotulo="Fornecedor">{d.fornecedor?.nome ?? <span className="suave">—</span>}</td>
                    <td data-rotulo="Valor" className="tabela__numero">
                      {formatarMoeda(d.valor)}
                    </td>
                    <td className="tabela__acoes">
                      {d.conta_pagar_id ? (
                        <span className="etiqueta" title="Gerada pelo pagamento de uma conta. Altere pela conta.">
                          Conta paga
                        </span>
                      ) : (
                        <>
                          <button
                            type="button"
                            className="link"
                            onClick={() => setEdicao({ modo: 'editar', despesa: d })}
                            aria-label={`Editar ${d.descricao}`}
                          >
                            Editar
                          </button>
                          <button
                            type="button"
                            className="link link--perigo"
                            onClick={() => void excluir(d)}
                            aria-label={`Excluir ${d.descricao}`}
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
