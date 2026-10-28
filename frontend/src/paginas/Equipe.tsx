import { useState, type FormEvent } from 'react'
import { useArea } from '../contexto'
import { useAcao } from '../hooks/useAcao'
import { useCarregar } from '../hooks/useCarregar'
import { adicionarMembro, alterarPapel, listarMembros, removerMembro, type Membro, type Papel } from '../recursos/equipe'

const PAPEIS: Record<Papel, string> = { proprietario: 'Proprietário', membro: 'Membro' }

export function Equipe() {
  const { restaurante, recarregarRestaurantes } = useArea()
  const lista = useCarregar(`equipe-${restaurante.id}`, () => listarMembros(restaurante.id))
  const [email, setEmail] = useState('')
  const [papel, setPapel] = useState<Papel>('membro')
  const { executar: executarAcao, ocupado, erro } = useAcao()
  const proprietario = restaurante.papel === 'proprietario'

  function executar(acao: () => Promise<unknown>, afetaVoce = false): Promise<boolean> {
    // Se a mudança foi na própria pessoa (saiu ou mudou de papel), a lista de restaurantes muda.
    return executarAcao(acao, afetaVoce ? recarregarRestaurantes : lista.recarregar)
  }

  async function adicionar(evento: FormEvent) {
    evento.preventDefault()
    if (await executar(() => adicionarMembro(restaurante.id, email, papel))) setEmail('')
  }

  function remover(m: Membro) {
    const pergunta = m.voce
      ? `Sair de ${restaurante.nome}? Você perderá o acesso aos dados deste restaurante.`
      : `Remover ${m.nome} da equipe?`
    if (window.confirm(pergunta)) void executar(() => removerMembro(restaurante.id, m.usuario_id), m.voce)
  }

  return (
    <section className="pagina-secao" aria-labelledby="titulo-equipe">
      <header className="pagina-secao__cabecalho">
        <h2 id="titulo-equipe">Equipe</h2>
      </header>
      <p className="pagina-secao__ajuda">
        Quem faz parte da equipe vê e registra os dados financeiros deste restaurante. Só proprietários adicionam ou
        removem pessoas.
      </p>

      {proprietario && (
        <form className="cartao filtros" onSubmit={adicionar}>
          <label className="campo">
            <span className="campo__rotulo">E-mail da pessoa</span>
            <input
              className="campo__entrada"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              maxLength={254}
              required
            />
          </label>
          <label className="campo">
            <span className="campo__rotulo">Papel</span>
            <select className="campo__entrada" value={papel} onChange={(e) => setPapel(e.target.value as Papel)}>
              <option value="membro">Membro</option>
              <option value="proprietario">Proprietário</option>
            </select>
          </label>
          <button type="submit" className="botao botao--primario" disabled={ocupado}>
            Adicionar
          </button>
          <span className="campo__ajuda campo--largo">A pessoa precisa já ter criado uma conta neste sistema.</span>
        </form>
      )}

      {(erro || lista.erro) && (
        <p className="alerta alerta--erro" role="alert">
          {erro ?? lista.erro}
        </p>
      )}

      {lista.dados && (
        <ul className="cartao lista-simples" aria-busy={lista.carregando}>
          {lista.dados.map((m) => (
            <li key={m.usuario_id}>
              <span>
                {m.nome}
                {m.voce && <span className="etiqueta">Você</span>}
                <span className="tabela__detalhe">{m.email}</span>
              </span>
              <span className="lista-simples__acoes">
                {proprietario ? (
                  <select
                    className="campo__entrada"
                    aria-label={`Papel de ${m.nome}`}
                    value={m.papel}
                    disabled={ocupado}
                    onChange={(e) =>
                      void executar(() => alterarPapel(restaurante.id, m.usuario_id, e.target.value as Papel), m.voce)
                    }
                  >
                    <option value="membro">Membro</option>
                    <option value="proprietario">Proprietário</option>
                  </select>
                ) : (
                  <span className="etiqueta">{PAPEIS[m.papel]}</span>
                )}
                {(proprietario || m.voce) && (
                  <button
                    type="button"
                    className="link link--perigo"
                    aria-label={m.voce ? 'Sair do restaurante' : `Remover ${m.nome}`}
                    disabled={ocupado}
                    onClick={() => remover(m)}
                  >
                    {m.voce ? 'Sair' : 'Remover'}
                  </button>
                )}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
