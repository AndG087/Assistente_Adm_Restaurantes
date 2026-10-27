import { useState, type FormEvent } from 'react'

interface FormRestauranteProps {
  titulo: string
  descricao?: string
  onCriar: (nome: string, cnpj: string) => Promise<unknown>
  onCancelar?: () => void
}

export function FormRestaurante({ titulo, descricao, onCriar, onCancelar }: FormRestauranteProps) {
  const [nome, setNome] = useState('')
  const [cnpj, setCnpj] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [erro, setErro] = useState<string | null>(null)

  async function aoSubmeter(evento: FormEvent) {
    evento.preventDefault()
    setEnviando(true)
    setErro(null)
    try {
      await onCriar(nome, cnpj.trim())
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'Erro inesperado.')
      setEnviando(false)
    }
  }

  return (
    <section className="cartao" aria-labelledby="titulo-restaurante">
      <form className="formulario" onSubmit={aoSubmeter}>
        <h2 id="titulo-restaurante" className="formulario__titulo">
          {titulo}
        </h2>
        {descricao && <p className="formulario__descricao">{descricao}</p>}

        <label className="campo">
          <span className="campo__rotulo">Nome do restaurante</span>
          <input
            className="campo__entrada"
            value={nome}
            onChange={(e) => setNome(e.target.value)}
            minLength={2}
            maxLength={120}
            required
          />
        </label>

        <label className="campo">
          <span className="campo__rotulo">CNPJ (opcional)</span>
          <input
            className="campo__entrada"
            value={cnpj}
            onChange={(e) => setCnpj(e.target.value)}
            inputMode="numeric"
            placeholder="00.000.000/0000-00"
            maxLength={18}
          />
        </label>

        {erro && (
          <p className="alerta alerta--erro" role="alert">
            {erro}
          </p>
        )}

        <div className="formulario__acoes">
          {onCancelar && (
            <button type="button" className="botao botao--secundario" onClick={onCancelar}>
              Cancelar
            </button>
          )}
          <button type="submit" className="botao botao--primario" disabled={enviando}>
            {enviando ? 'Salvando…' : 'Cadastrar restaurante'}
          </button>
        </div>
      </form>
    </section>
  )
}
