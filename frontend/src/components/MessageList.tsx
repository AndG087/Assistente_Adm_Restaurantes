import { useEffect, useRef } from 'react'
import type { RespostaAssistente, TabelaResposta } from '../recursos/assistente'

export interface Mensagem {
  id: number
  autor: 'usuario' | 'ia' | 'erro'
  texto: string
  origem?: RespostaAssistente['origem']
  consulta?: string | null
  tabela?: TabelaResposta | null
}

interface MessageListProps {
  mensagens: Mensagem[]
  aguardandoResposta: boolean
  // Ausente enquanto uma resposta está sendo gerada (as sugestões ficam desabilitadas).
  onSugestao?: (pergunta: string) => void
}

const ROTULOS: Record<Mensagem['autor'], string> = {
  usuario: 'Você',
  ia: 'Assistente',
  erro: 'Erro',
}

const SUGESTOES = [
  'Quanto gastei este mês?',
  'Em que categorias gastei mais?',
  'Quais contas vencem esta semana?',
  'Tenho contas vencidas?',
  'Compare os gastos deste mês com o mês passado',
]

function Origem({ mensagem }: { mensagem: Mensagem }) {
  if (mensagem.origem === 'dados') {
    return (
      <span className="mensagem__origem mensagem__origem--dados">
        Dados do restaurante{mensagem.consulta ? ` · ${mensagem.consulta}` : ''}
      </span>
    )
  }
  if (mensagem.origem === 'conversa') {
    return <span className="mensagem__origem">Conversa geral · sem acesso aos dados do restaurante</span>
  }
  return null
}

function Tabela({ tabela }: { tabela: TabelaResposta }) {
  return (
    <div className="mensagem__tabela">
      <table>
        <thead>
          <tr>
            {tabela.colunas.map((coluna) => (
              <th key={coluna} scope="col">
                {coluna}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {tabela.linhas.map((linha, i) => (
            <tr key={i}>
              {linha.map((celula, j) => (
                <td key={j}>{celula}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function MessageList({ mensagens, aguardandoResposta, onSugestao }: MessageListProps) {
  const fimRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    fimRef.current?.scrollIntoView?.({ behavior: 'smooth', block: 'end' })
  }, [mensagens, aguardandoResposta])

  if (mensagens.length === 0 && !aguardandoResposta) {
    return (
      <div className="mensagens mensagens--vazia">
        <p className="mensagens__dica-titulo">Pergunte sobre as finanças do restaurante</p>
        <p className="mensagens__dica">
          Os valores vêm do banco de dados e são calculados pelo sistema; a IA local só ajuda a entender a
          pergunta. Nada é enviado para a internet.
        </p>
        <div className="sugestoes" aria-label="Perguntas de exemplo">
          {SUGESTOES.map((pergunta) => (
            <button
              key={pergunta}
              type="button"
              className="sugestoes__item"
              disabled={!onSugestao}
              onClick={() => onSugestao?.(pergunta)}
            >
              {pergunta}
            </button>
          ))}
        </div>
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
          <Origem mensagem={mensagem} />
          <p className="mensagem__texto">{mensagem.texto}</p>
          {mensagem.tabela && <Tabela tabela={mensagem.tabela} />}
        </div>
      ))}

      {aguardandoResposta && (
        <div className="mensagem mensagem--ia mensagem--carregando" aria-label="O assistente está preparando a resposta">
          <span className="mensagem__autor">Assistente</span>
          <span className="digitando" aria-hidden="true">
            <span />
            <span />
            <span />
          </span>
          <span className="mensagem__texto">Preparando a resposta…</span>
        </div>
      )}
      <div ref={fimRef} />
    </div>
  )
}
