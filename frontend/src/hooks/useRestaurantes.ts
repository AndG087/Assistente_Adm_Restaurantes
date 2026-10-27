import { useCallback, useEffect, useState } from 'react'
import { criarRestaurante, listarRestaurantes, type Restaurante } from '../api'

const CHAVE_SELECIONADO = 'restaurante-selecionado'

// Preferência apenas de conveniência: se o navegador bloquear o armazenamento, a página funciona igual.
function lerSelecionadoSalvo(): number | null {
  try {
    const valor = Number(localStorage.getItem(CHAVE_SELECIONADO))
    return Number.isInteger(valor) && valor > 0 ? valor : null
  } catch {
    return null
  }
}

function salvarSelecionado(id: number) {
  try {
    localStorage.setItem(CHAVE_SELECIONADO, String(id))
  } catch {
    // ignora
  }
}

export interface EstadoRestaurantes {
  carregando: boolean
  erro: unknown
  restaurantes: Restaurante[]
  selecionado: Restaurante | null
  selecionar: (id: number) => void
  criar: (nome: string, cnpj: string) => Promise<Restaurante>
  recarregar: () => void
}

export function useRestaurantes(): EstadoRestaurantes {
  const [carregando, setCarregando] = useState(true)
  const [erro, setErro] = useState<unknown>(null)
  const [restaurantes, setRestaurantes] = useState<Restaurante[]>([])
  const [selecionadoId, setSelecionadoId] = useState<number | null>(lerSelecionadoSalvo)
  const [versao, setVersao] = useState(0)

  useEffect(() => {
    let ativo = true
    listarRestaurantes()
      .then((lista) => {
        if (!ativo) return
        setRestaurantes(lista)
        setErro(null)
      })
      .catch((e: unknown) => {
        if (ativo) setErro(e)
      })
      .finally(() => {
        if (ativo) setCarregando(false)
      })
    return () => {
      ativo = false
    }
  }, [versao])

  const selecionar = useCallback((id: number) => {
    setSelecionadoId(id)
    salvarSelecionado(id)
  }, [])

  const criar = useCallback(
    async (nome: string, cnpj: string) => {
      const novo = await criarRestaurante(nome, cnpj)
      setRestaurantes((lista) => [...lista, novo].sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR')))
      selecionar(novo.id)
      return novo
    },
    [selecionar],
  )

  const recarregar = useCallback(() => {
    setCarregando(true)
    setVersao((v) => v + 1)
  }, [])

  // Se o id salvo não pertence mais ao usuário (ou nada foi escolhido), usa o primeiro da lista.
  const selecionado = restaurantes.find((r) => r.id === selecionadoId) ?? restaurantes[0] ?? null

  return { carregando, erro, restaurantes, selecionado, selecionar, criar, recarregar }
}
