import { useState, type FormEvent, type ReactNode } from 'react'
import { useArea } from '../contexto'
import { useCarregar } from '../hooks/useCarregar'
import { listarCategorias, listarFornecedores } from '../recursos/cadastros'
import type { DadosLancamento, Referencia } from '../recursos/financeiro'
import { hojeIso, valorParaApi, valorParaCampo } from '../utils/formato'

/** Valores iniciais do formulário; ao editar, vêm do lançamento existente. */
export interface LancamentoInicial {
  descricao: string
  valor: string
  data: string
  categoria: Referencia | null
  fornecedor: Referencia | null
  numero_documento: string | null
  observacoes: string | null
}

interface FormLancamentoProps {
  titulo: string
  rotuloData: string
  inicial?: LancamentoInicial
  onSalvar: (dados: DadosLancamento, data: string) => Promise<unknown>
  onCancelar: () => void
  // Conteúdo extra logo abaixo do título (ex.: escolha entre despesa e conta na conferência).
  cabecalho?: ReactNode
  rotuloSalvar?: string
  rotuloCancelar?: string
}

/** Formulário comum a despesas e contas a pagar. */
export function FormLancamento({
  titulo,
  rotuloData,
  inicial,
  onSalvar,
  onCancelar,
  cabecalho,
  rotuloSalvar = 'Salvar',
  rotuloCancelar = 'Cancelar',
}: FormLancamentoProps) {
  const { restaurante, mensagemDeErro } = useArea()
  const [descricao, setDescricao] = useState(inicial?.descricao ?? '')
  const [valor, setValor] = useState(inicial ? valorParaCampo(inicial.valor) : '')
  const [data, setData] = useState(inicial?.data ?? hojeIso())
  const [categoriaId, setCategoriaId] = useState(inicial?.categoria?.id ?? null)
  const [fornecedorId, setFornecedorId] = useState(inicial?.fornecedor?.id ?? null)
  const [numeroDocumento, setNumeroDocumento] = useState(inicial?.numero_documento ?? '')
  const [observacoes, setObservacoes] = useState(inicial?.observacoes ?? '')
  const [enviando, setEnviando] = useState(false)
  const [erro, setErro] = useState<string | null>(null)

  const opcoes = useCarregar(`opcoes-${restaurante.id}`, async () => {
    const [categorias, fornecedores] = await Promise.all([
      listarCategorias(restaurante.id),
      listarFornecedores(restaurante.id),
    ])
    return { categorias, fornecedores }
  })

  // Ao editar, a categoria/fornecedor atual pode estar inativa: continua aparecendo para não ser perdida.
  function comAtual(lista: Referencia[], atual: Referencia | null | undefined): Referencia[] {
    return atual && !lista.some((item) => item.id === atual.id) ? [...lista, atual] : lista
  }
  const categorias = comAtual(opcoes.dados?.categorias ?? [], inicial?.categoria)
  const fornecedores = comAtual(opcoes.dados?.fornecedores ?? [], inicial?.fornecedor)

  async function aoSubmeter(evento: FormEvent) {
    evento.preventDefault()
    const valorApi = valorParaApi(valor)
    if (!valorApi) {
      setErro('Informe um valor válido, maior que zero (ex.: 1.234,56).')
      return
    }
    setEnviando(true)
    setErro(null)
    try {
      await onSalvar(
        {
          descricao,
          valor: valorApi,
          categoria_id: categoriaId,
          fornecedor_id: fornecedorId,
          numero_documento: numeroDocumento.trim() || null,
          observacoes: observacoes.trim() || null,
        },
        data,
      )
    } catch (e) {
      setErro(mensagemDeErro(e))
      setEnviando(false)
    }
  }

  return (
    <section className="cartao painel-form" aria-labelledby="titulo-lancamento">
      <form className="formulario formulario--grade" onSubmit={aoSubmeter}>
        <h2 id="titulo-lancamento" className="formulario__titulo">
          {titulo}
        </h2>
        {cabecalho && <div className="campo--largo">{cabecalho}</div>}

        <label className="campo campo--largo">
          <span className="campo__rotulo">Descrição</span>
          <input
            className="campo__entrada"
            value={descricao}
            onChange={(e) => setDescricao(e.target.value)}
            minLength={2}
            maxLength={200}
            required
          />
        </label>

        <label className="campo">
          <span className="campo__rotulo">Valor (R$)</span>
          <input
            className="campo__entrada"
            value={valor}
            onChange={(e) => setValor(e.target.value)}
            inputMode="decimal"
            placeholder="0,00"
            required
          />
        </label>

        <label className="campo">
          <span className="campo__rotulo">{rotuloData}</span>
          <input
            className="campo__entrada"
            type="date"
            value={data}
            onChange={(e) => setData(e.target.value)}
            min="2000-01-01"
            max="2100-12-31"
            required
          />
        </label>

        <label className="campo">
          <span className="campo__rotulo">Categoria</span>
          <select
            className="campo__entrada"
            value={categoriaId ?? ''}
            onChange={(e) => setCategoriaId(e.target.value ? Number(e.target.value) : null)}
          >
            <option value="">Sem categoria</option>
            {categorias.map((c) => (
              <option key={c.id} value={c.id}>
                {c.nome}
              </option>
            ))}
          </select>
        </label>

        <label className="campo">
          <span className="campo__rotulo">Fornecedor</span>
          <select
            className="campo__entrada"
            value={fornecedorId ?? ''}
            onChange={(e) => setFornecedorId(e.target.value ? Number(e.target.value) : null)}
          >
            <option value="">Nenhum</option>
            {fornecedores.map((f) => (
              <option key={f.id} value={f.id}>
                {f.nome}
              </option>
            ))}
          </select>
        </label>

        <label className="campo">
          <span className="campo__rotulo">Nº do documento (opcional)</span>
          <input
            className="campo__entrada"
            value={numeroDocumento}
            onChange={(e) => setNumeroDocumento(e.target.value)}
            placeholder="Nota fiscal, boleto…"
            maxLength={60}
          />
        </label>

        <label className="campo campo--largo">
          <span className="campo__rotulo">Observações (opcional)</span>
          <textarea
            className="campo__entrada"
            value={observacoes}
            onChange={(e) => setObservacoes(e.target.value)}
            maxLength={500}
            rows={2}
          />
        </label>

        {(erro || opcoes.erro) && (
          <p className="alerta alerta--erro campo--largo" role="alert">
            {erro ?? `Não foi possível carregar categorias e fornecedores. ${opcoes.erro}`}
          </p>
        )}

        <div className="formulario__acoes campo--largo">
          <button type="button" className="botao botao--secundario" onClick={onCancelar}>
            {rotuloCancelar}
          </button>
          <button type="submit" className="botao botao--primario" disabled={enviando}>
            {enviando ? 'Salvando…' : rotuloSalvar}
          </button>
        </div>
      </form>
    </section>
  )
}
