import { useState, type FormEvent } from 'react'
import { useArea } from '../contexto'
import { useCarregar } from '../hooks/useCarregar'
import { atualizarCategoria, criarCategoria, listarCategorias, type Categoria } from '../recursos/cadastros'

export function Categorias() {
  const { restaurante, mensagemDeErro } = useArea()
  const lista = useCarregar(`categorias-${restaurante.id}`, () => listarCategorias(restaurante.id, true))
  const [nova, setNova] = useState('')
  const [editando, setEditando] = useState<{ id: number; nome: string } | null>(null)
  const [erro, setErro] = useState<string | null>(null)

  async function executar(acao: () => Promise<unknown>): Promise<boolean> {
    setErro(null)
    try {
      await acao()
      lista.recarregar()
      return true
    } catch (e) {
      setErro(mensagemDeErro(e))
      return false
    }
  }

  async function adicionar(evento: FormEvent) {
    evento.preventDefault()
    if (await executar(() => criarCategoria(restaurante.id, nova))) setNova('')
  }

  async function renomear(evento: FormEvent, categoria: Categoria) {
    evento.preventDefault()
    if (!editando) return
    if (await executar(() => atualizarCategoria(restaurante.id, categoria.id, editando.nome, categoria.ativo))) {
      setEditando(null)
    }
  }

  return (
    <section className="pagina-secao" aria-labelledby="titulo-categorias">
      <header className="pagina-secao__cabecalho">
        <h2 id="titulo-categorias">Categorias financeiras</h2>
      </header>

      <form className="cartao filtros" onSubmit={adicionar}>
        <label className="campo">
          <span className="campo__rotulo">Nova categoria</span>
          <input
            className="campo__entrada"
            value={nova}
            onChange={(e) => setNova(e.target.value)}
            minLength={2}
            maxLength={60}
            required
          />
        </label>
        <button type="submit" className="botao botao--primario">
          Adicionar
        </button>
      </form>

      {(erro || lista.erro) && (
        <p className="alerta alerta--erro" role="alert">
          {erro ?? lista.erro}
        </p>
      )}

      {lista.dados && (
        <ul className="cartao lista-simples" aria-busy={lista.carregando}>
          {lista.dados.map((c) => (
            <li key={c.id} className={c.ativo ? undefined : 'tabela__linha--inativa'}>
              {editando?.id === c.id ? (
                <form className="lista-simples__edicao" onSubmit={(e) => void renomear(e, c)}>
                  <input
                    className="campo__entrada"
                    aria-label={`Novo nome para ${c.nome}`}
                    value={editando.nome}
                    onChange={(e) => setEditando({ id: c.id, nome: e.target.value })}
                    minLength={2}
                    maxLength={60}
                    required
                    autoFocus
                  />
                  <button type="submit" className="link">
                    Salvar
                  </button>
                  <button type="button" className="link" onClick={() => setEditando(null)}>
                    Cancelar
                  </button>
                </form>
              ) : (
                <>
                  <span>
                    {c.nome}
                    {!c.ativo && <span className="etiqueta">Inativa</span>}
                  </span>
                  <span className="lista-simples__acoes">
                    <button
                      type="button"
                      className="link"
                      aria-label={`Renomear ${c.nome}`}
                      onClick={() => setEditando({ id: c.id, nome: c.nome })}
                    >
                      Renomear
                    </button>
                    <button
                      type="button"
                      className="link"
                      aria-label={`${c.ativo ? 'Inativar' : 'Reativar'} ${c.nome}`}
                      onClick={() => void executar(() => atualizarCategoria(restaurante.id, c.id, c.nome, !c.ativo))}
                    >
                      {c.ativo ? 'Inativar' : 'Reativar'}
                    </button>
                  </span>
                </>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
