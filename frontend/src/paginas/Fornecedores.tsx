import { useState, type FormEvent } from 'react'
import { useArea } from '../contexto'
import { useCarregar } from '../hooks/useCarregar'
import { listarFornecedores, salvarFornecedor, type DadosFornecedor, type Fornecedor } from '../recursos/cadastros'
import { formatarDocumento } from '../utils/formato'

const VAZIO: DadosFornecedor = { nome: '', documento: '', telefone: '', email: '', observacoes: '', ativo: true }

export function Fornecedores() {
  const { restaurante } = useArea()
  const [busca, setBusca] = useState('')
  const [incluirInativos, setIncluirInativos] = useState(false)
  const [editando, setEditando] = useState<Fornecedor | 'novo' | null>(null)

  const filtros = { busca: busca.trim(), incluir_inativos: incluirInativos }
  const lista = useCarregar(`${restaurante.id}|${JSON.stringify(filtros)}`, () =>
    listarFornecedores(restaurante.id, filtros),
  )

  if (editando) {
    return (
      <FormFornecedor
        fornecedor={editando === 'novo' ? null : editando}
        onFechar={(salvou) => {
          setEditando(null)
          if (salvou) lista.recarregar()
        }}
      />
    )
  }

  return (
    <section className="pagina-secao" aria-labelledby="titulo-fornecedores">
      <header className="pagina-secao__cabecalho">
        <h2 id="titulo-fornecedores">Fornecedores</h2>
        <button type="button" className="botao botao--primario" onClick={() => setEditando('novo')}>
          Novo fornecedor
        </button>
      </header>

      <div className="cartao filtros">
        <label className="campo">
          <span className="campo__rotulo">Buscar</span>
          <input
            className="campo__entrada"
            type="search"
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            placeholder="Nome ou CPF/CNPJ"
            maxLength={100}
          />
        </label>
        <label className="campo-checkbox">
          <input type="checkbox" checked={incluirInativos} onChange={(e) => setIncluirInativos(e.target.checked)} />
          Mostrar inativos
        </label>
      </div>

      {lista.erro && (
        <p className="alerta alerta--erro" role="alert">
          {lista.erro}
        </p>
      )}

      {lista.dados && (
        <div className="cartao tabela-container" aria-busy={lista.carregando}>
          {lista.dados.length === 0 ? (
            <p className="vazio">Nenhum fornecedor encontrado.</p>
          ) : (
            <table className="tabela">
              <thead>
                <tr>
                  <th scope="col">Nome</th>
                  <th scope="col">CPF/CNPJ</th>
                  <th scope="col">Contato</th>
                  <th scope="col">
                    <span className="visualmente-oculto">Ações</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {lista.dados.map((f) => (
                  <tr key={f.id} className={f.ativo ? undefined : 'tabela__linha--inativa'}>
                    <td data-rotulo="Nome">
                      {f.nome}
                      {!f.ativo && <span className="etiqueta">Inativo</span>}
                    </td>
                    <td data-rotulo="CPF/CNPJ">{formatarDocumento(f.documento) || <span className="suave">—</span>}</td>
                    <td data-rotulo="Contato">
                      {[f.telefone, f.email].filter(Boolean).join(' · ') || <span className="suave">—</span>}
                    </td>
                    <td className="tabela__acoes">
                      <button
                        type="button"
                        className="link"
                        aria-label={`Editar ${f.nome}`}
                        onClick={() => setEditando(f)}
                      >
                        Editar
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </section>
  )
}

interface FormFornecedorProps {
  fornecedor: Fornecedor | null
  onFechar: (salvou: boolean) => void
}

function FormFornecedor({ fornecedor, onFechar }: FormFornecedorProps) {
  const { restaurante, mensagemDeErro } = useArea()
  const [dados, setDados] = useState<DadosFornecedor>(() =>
    fornecedor
      ? {
          ...fornecedor,
          documento: formatarDocumento(fornecedor.documento),
          telefone: fornecedor.telefone ?? '',
          email: fornecedor.email ?? '',
          observacoes: fornecedor.observacoes ?? '',
        }
      : VAZIO,
  )
  const [enviando, setEnviando] = useState(false)
  const [erro, setErro] = useState<string | null>(null)

  function alterar<K extends keyof DadosFornecedor>(campo: K, valor: DadosFornecedor[K]) {
    setDados((atual) => ({ ...atual, [campo]: valor }))
  }

  async function aoSubmeter(evento: FormEvent) {
    evento.preventDefault()
    setEnviando(true)
    setErro(null)
    try {
      await salvarFornecedor(restaurante.id, fornecedor?.id ?? null, dados)
      onFechar(true)
    } catch (e) {
      setErro(mensagemDeErro(e))
      setEnviando(false)
    }
  }

  const texto = (campo: 'documento' | 'telefone' | 'email' | 'observacoes') => dados[campo] ?? ''

  return (
    <section className="cartao painel-form" aria-labelledby="titulo-fornecedor">
      <form className="formulario formulario--grade" onSubmit={aoSubmeter}>
        <h2 id="titulo-fornecedor" className="formulario__titulo">
          {fornecedor ? 'Editar fornecedor' : 'Novo fornecedor'}
        </h2>

        <label className="campo campo--largo">
          <span className="campo__rotulo">Nome</span>
          <input
            className="campo__entrada"
            value={dados.nome}
            onChange={(e) => alterar('nome', e.target.value)}
            minLength={2}
            maxLength={150}
            required
          />
        </label>
        <label className="campo">
          <span className="campo__rotulo">CPF ou CNPJ (opcional)</span>
          <input
            className="campo__entrada"
            value={texto('documento')}
            onChange={(e) => alterar('documento', e.target.value)}
            inputMode="numeric"
            maxLength={18}
          />
        </label>
        <label className="campo">
          <span className="campo__rotulo">Telefone (opcional)</span>
          <input
            className="campo__entrada"
            type="tel"
            value={texto('telefone')}
            onChange={(e) => alterar('telefone', e.target.value)}
            maxLength={20}
          />
        </label>
        <label className="campo campo--largo">
          <span className="campo__rotulo">E-mail (opcional)</span>
          <input
            className="campo__entrada"
            type="email"
            value={texto('email')}
            onChange={(e) => alterar('email', e.target.value)}
            maxLength={254}
          />
        </label>
        <label className="campo campo--largo">
          <span className="campo__rotulo">Observações (opcional)</span>
          <textarea
            className="campo__entrada"
            value={texto('observacoes')}
            onChange={(e) => alterar('observacoes', e.target.value)}
            maxLength={500}
            rows={2}
          />
        </label>
        {fornecedor && (
          <label className="campo-checkbox campo--largo">
            <input type="checkbox" checked={dados.ativo} onChange={(e) => alterar('ativo', e.target.checked)} />
            Fornecedor ativo (inativos não aparecem para novos lançamentos)
          </label>
        )}

        {erro && (
          <p className="alerta alerta--erro campo--largo" role="alert">
            {erro}
          </p>
        )}

        <div className="formulario__acoes campo--largo">
          <button type="button" className="botao botao--secundario" onClick={() => onFechar(false)}>
            Cancelar
          </button>
          <button type="submit" className="botao botao--primario" disabled={enviando}>
            {enviando ? 'Salvando…' : 'Salvar'}
          </button>
        </div>
      </form>
    </section>
  )
}
