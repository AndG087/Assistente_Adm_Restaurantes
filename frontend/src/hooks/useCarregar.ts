import { useCallback, useEffect, useEffectEvent, useState } from 'react'
import { useArea } from '../contexto'

export interface Carregamento<T> {
  dados: T | null
  erro: string | null
  // true enquanto a consulta atual (chave + recarga) não terminou; os dados anteriores continuam visíveis
  carregando: boolean
  recarregar: () => void
}

/**
 * Carrega dados da API e recarrega quando `chave` muda (ex.: filtros serializados).
 * Respostas que chegam fora de ordem são descartadas.
 */
export function useCarregar<T>(chave: string, carregar: () => Promise<T>): Carregamento<T> {
  const { mensagemDeErro } = useArea()
  const [dados, setDados] = useState<T | null>(null)
  const [erro, setErro] = useState<string | null>(null)
  const [versao, setVersao] = useState(0)
  const [concluida, setConcluida] = useState<string | null>(null)

  const alvo = `${versao}|${chave}`
  const executar = useEffectEvent(carregar)
  const tratarErro = useEffectEvent(mensagemDeErro)

  useEffect(() => {
    let ativo = true
    executar()
      .then((resultado) => {
        if (!ativo) return
        setDados(resultado)
        setErro(null)
      })
      .catch((e: unknown) => {
        if (ativo) setErro(tratarErro(e))
      })
      .finally(() => {
        if (ativo) setConcluida(alvo)
      })
    return () => {
      ativo = false
    }
  }, [alvo])

  const recarregar = useCallback(() => setVersao((v) => v + 1), [])

  return { dados, erro, carregando: concluida !== alvo, recarregar }
}
