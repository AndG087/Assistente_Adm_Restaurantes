import { createContext, useContext } from 'react'
import { ApiError, type Restaurante } from './api'

export interface ContextoArea {
  restaurante: Restaurante
  sessaoExpirou: () => void
}

export const AreaContext = createContext<ContextoArea | null>(null)

/** Restaurante selecionado e ações comuns às páginas da área logada. */
export function useArea() {
  const contexto = useContext(AreaContext)
  if (!contexto) throw new Error('useArea deve ser usado dentro da área logada.')

  /** Converte um erro em mensagem; se a sessão expirou, volta para o login. */
  function mensagemDeErro(erro: unknown): string {
    if (erro instanceof ApiError && erro.status === 401) {
      contexto!.sessaoExpirou()
    }
    return erro instanceof Error ? erro.message : 'Ocorreu um erro inesperado.'
  }

  return { ...contexto, mensagemDeErro }
}
