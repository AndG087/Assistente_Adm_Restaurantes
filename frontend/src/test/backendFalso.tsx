import { render } from '@testing-library/react'
import type { ReactNode } from 'react'
import { vi } from 'vitest'
import type { Restaurante } from '../api'
import { AreaContext } from '../contexto'

export type Rota = (init: RequestInit | undefined, url: URL) => Response | Promise<Response>

export function json(corpo: unknown, status = 200): Response {
  return new Response(JSON.stringify(corpo), { status, headers: { 'Content-Type': 'application/json' } })
}

export const semConteudo = () => new Response(null, { status: 204 })

/**
 * Substitui o fetch por um backend falso. As chaves são "MÉTODO /caminho", em que * casa com
 * um número (ex.: "GET /api/restaurantes/*\/despesas"). Os parâmetros ?de=... ficam em url.searchParams.
 * Rotas não cadastradas se comportam como backend fora do ar.
 */
export function simularBackend(rotas: Record<string, Rota>) {
  const padroes = Object.entries(rotas).map(([chave, rota]) => {
    const [metodo, caminho] = chave.split(' ')
    const regex = new RegExp(`^${caminho.replace(/[.?+]/g, '\\$&').replace(/\*/g, '\\d+')}$`)
    return { metodo, regex, rota }
  })

  const fetchFalso = vi.fn(async (entrada: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(String(entrada), 'http://teste.local')
    const metodo = init?.method ?? 'GET'
    const encontrado = padroes.find((p) => p.metodo === metodo && p.regex.test(url.pathname))
    if (!encontrado) throw new TypeError('Failed to fetch')
    return encontrado.rota(init, url)
  })
  vi.stubGlobal('fetch', fetchFalso)
  return fetchFalso
}

type FetchFalso = ReturnType<typeof simularBackend>

/** Chamadas feitas a um método + caminho (sem os parâmetros de consulta). */
export function chamadas(fetchFalso: FetchFalso, metodo: string, caminho: string) {
  return fetchFalso.mock.calls
    .map(([entrada, init]) => ({ url: new URL(String(entrada), 'http://teste.local'), init }))
    .filter(({ url, init }) => url.pathname === caminho && (init?.method ?? 'GET') === metodo)
}

export function corpoEnviado(chamada: { init?: RequestInit }): unknown {
  return JSON.parse(String(chamada.init?.body))
}

export const RESTAURANTE: Restaurante = { id: 10, nome: 'Cantina da Ana', cnpj: '11222333000181', papel: 'proprietario' }

/** Renderiza uma página da área logada já com o restaurante selecionado. */
export function renderizarNaArea(ui: ReactNode, restaurante: Restaurante = RESTAURANTE) {
  const sessaoExpirou = vi.fn()
  const recarregarRestaurantes = vi.fn()
  return {
    sessaoExpirou,
    recarregarRestaurantes,
    ...render(
      <AreaContext.Provider value={{ restaurante, sessaoExpirou, recarregarRestaurantes }}>{ui}</AreaContext.Provider>,
    ),
  }
}
