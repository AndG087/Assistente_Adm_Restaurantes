import { useEffect, useRef } from 'react'

export interface Mensagem {
  id: number
  autor: 'usuario' | 'ia' | 'erro'
  texto: string
}

interface MessageListProps {
  mensagens: Mensagem[]
  aguardandoResposta: boolean
}

const ROTULOS: Record<Mensagem['autor'], string> = {
  usuario: 'Você',
  ia: 'IA',
  erro: 'Erro',
}

export function MessageList({ mensagens, aguardandoResposta }: MessageListProps) {
  const fimRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    fimRef.current?.scrollIntoView?.({ behavior: 'smooth', block: 'end' })
  }, [mensagens, aguardandoResposta])

  if (mensagens.length === 0 && !aguardandoResposta) {
    return (
      <div className="mensagens mensagens--vazia">
        <p className="mensagens__dica-titulo">Converse com o assistente local</p>
        <p className="mensagens__dica">
          Nesta versão a IA ainda não acessa dados do restaurante. As mensagens são processadas pelo modelo
          executado no seu computador, sem envio para serviços externos.
        </p>
      </div>
    )
  }

  return (
    <div className="mensagens" aria-live="polite">
      {mensagens.map((mensagem) => (
        <div
          key={mensagem.id}
          className={`mensagem mensagem--${mensagem.autor}`}
          role={mensagem.autor === 'erro' ? 'alert' : undefined}
        >
          <span className="mensagem__autor">{ROTULOS[mensagem.autor]}</span>
          <p className="mensagem__texto">{mensagem.texto}</p>
        </div>
      ))}

      {aguardandoResposta && (
        <div className="mensagem mensagem--ia mensagem--carregando" aria-label="A IA está gerando a resposta">
          <span className="mensagem__autor">IA</span>
          <span className="digitando" aria-hidden="true">
            <span />
            <span />
            <span />
          </span>
          <span className="mensagem__texto">Gerando resposta…</span>
        </div>
      )}
      <div ref={fimRef} />
    </div>
  )
}
