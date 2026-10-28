import { useRef, useState } from 'react'
import { ApiError, type IAStatusResponse } from '../api'
import { useArea } from '../contexto'
import { perguntarAssistente } from '../recursos/assistente'
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
    return 'A IA local (Ollama) está desligada. Perguntas sobre os dados (gastos, contas) continuam funcionando; a conversa geral volta quando ela for ligada.'
  }
  if (!statusIA.modelo_disponivel) {
    return `O modelo "${statusIA.modelo}" não está instalado. Perguntas sobre os dados continuam funcionando; para a conversa geral, instale com: ollama pull ${statusIA.modelo}`
  }
  return null
}

export function ChatWindow({ statusIA, onFalha, onSessaoExpirada }: ChatWindowProps) {
  const { restaurante } = useArea()
  const [mensagens, setMensagens] = useState<Mensagem[]>([])
  const [aguardando, setAguardando] = useState(false)
  const proximoId = useRef(1)

  function adicionar(mensagem: Omit<Mensagem, 'id'>) {
    const id = proximoId.current++
    setMensagens((anteriores) => [...anteriores, { id, ...mensagem }])
  }

  async function enviar(texto: string) {
    adicionar({ autor: 'usuario', texto })
    setAguardando(true)
    try {
      const r = await perguntarAssistente(restaurante.id, texto)
      adicionar({ autor: 'ia', texto: r.resposta, origem: r.origem, consulta: r.consulta, tabela: r.tabela })
    } catch (erro) {
      if (erro instanceof ApiError && erro.status === 401) {
        onSessaoExpirada()
        return
      }
      adicionar({ autor: 'erro', texto: erro instanceof ApiError ? erro.message : 'Ocorreu um erro inesperado.' })
      onFalha()
    } finally {
      setAguardando(false)
    }
  }

  const aviso = avisoDaIA(statusIA)

  return (
    <section className="chat" aria-label="Assistente">
      {aviso && <p className="chat__aviso">{aviso}</p>}
      <MessageList
        mensagens={mensagens}
        aguardandoResposta={aguardando}
        onSugestao={aguardando ? undefined : (pergunta) => void enviar(pergunta)}
      />
      <ChatInput onEnviar={enviar} desabilitado={aguardando} />
    </section>
  )
}
