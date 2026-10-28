import { enviarJson, requisitar } from '../api'

export interface TabelaResposta {
  colunas: string[]
  linhas: string[][]
}

export interface RespostaAssistente {
  resposta: string
  // dados: valores vindos do banco · conversa: IA sem acesso aos dados · ajuda: pergunta não entendida
  origem: 'dados' | 'conversa' | 'ajuda'
  consulta: string | null
  interpretado_por: 'regras' | 'ia' | null
  tabela: TabelaResposta | null
}

export function perguntarAssistente(restauranteId: number, mensagem: string): Promise<RespostaAssistente> {
  return requisitar(`/api/restaurantes/${restauranteId}/assistente`, enviarJson('POST', { mensagem }))
}
