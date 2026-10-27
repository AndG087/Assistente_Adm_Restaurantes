import { useState, type FormEvent, type KeyboardEvent } from 'react'
import { TAMANHO_MAXIMO_MENSAGEM } from '../api'

interface ChatInputProps {
  onEnviar: (mensagem: string) => void
  desabilitado: boolean
}

export function ChatInput({ onEnviar, desabilitado }: ChatInputProps) {
  const [texto, setTexto] = useState('')
  const mensagem = texto.trim()
  const podeEnviar = !desabilitado && mensagem.length > 0

  function enviar() {
    if (!podeEnviar) return
    onEnviar(mensagem)
    setTexto('')
  }

  function aoSubmeter(evento: FormEvent) {
    evento.preventDefault()
    enviar()
  }

  // Enter envia; Shift+Enter quebra a linha.
  function aoPressionarTecla(evento: KeyboardEvent<HTMLTextAreaElement>) {
    if (evento.key === 'Enter' && !evento.shiftKey && !evento.nativeEvent.isComposing) {
      evento.preventDefault()
      enviar()
    }
  }

  return (
    <form className="chat-input" onSubmit={aoSubmeter}>
      <label htmlFor="mensagem" className="visualmente-oculto">
        Mensagem para a IA
      </label>
      <textarea
        id="mensagem"
        className="chat-input__campo"
        placeholder="Escreva sua mensagem… (Enter envia, Shift+Enter quebra linha)"
        value={texto}
        maxLength={TAMANHO_MAXIMO_MENSAGEM}
        rows={2}
        onChange={(evento) => setTexto(evento.target.value)}
        onKeyDown={aoPressionarTecla}
      />
      <button type="submit" className="botao botao--primario" disabled={!podeEnviar}>
        Enviar
      </button>
    </form>
  )
}
