import { useRef, useState } from 'react'
import { ApiError, enviarMensagem, type IAStatusResponse } from '../api'
import { ChatInput } from './ChatInput'
import { MessageList, type Mensagem } from './MessageList'

interface ChatWindowProps {
  statusIA: IAStatusResponse | null
  onFalha: () => void
  onSessaoExpirada: () => void
}

function avisoDaIA(statusIA: IAStatusResponse | null): string | null {
  if (!statusIA) return null
  if (!statusIA.ollama_disponivel) {
    return 'O Ollama não está em execução. Inicie o Ollama para conversar com a IA; o restante do sistema continua funcionando.'
  }
  if (!statusIA.modelo_disponivel) {
    return `O modelo "${statusIA.modelo}" não está instalado. Instale com: ollama pull ${statusIA.modelo}`
  }
  return null
}

export function ChatWindow({ statusIA, onFalha, onSessaoExpirada }: ChatWindowProps) {
  const [mensagens, setMensagens] = useState<Mensagem[]>([])
  const [aguardando, setAguardando] = useState(false)
  const proximoId = useRef(1)

  function adicionar(autor: Mensagem['autor'], texto: string) {
    const id = proximoId.current++
    setMensagens((anteriores) => [...anteriores, { id, autor, texto }])
  }

  async function enviar(texto: string) {
    adicionar('usuario', texto)
    setAguardando(true)
    try {
      const { resposta } = await enviarMensagem(texto)
      adicionar('ia', resposta)
    } catch (erro) {
      if (erro instanceof ApiError && erro.status === 401) {
        onSessaoExpirada()
        return
      }
      adicionar('erro', erro instanceof ApiError ? erro.message : 'Ocorreu um erro inesperado.')
      onFalha()
    } finally {
      setAguardando(false)
    }
  }

  const aviso = avisoDaIA(statusIA)

  return (
    <section className="chat" aria-label="Chat com a IA local">
      {aviso && <p className="chat__aviso">{aviso}</p>}
      <MessageList mensagens={mensagens} aguardandoResposta={aguardando} />
      <ChatInput onEnviar={enviar} desabilitado={aguardando} />
    </section>
  )
}
