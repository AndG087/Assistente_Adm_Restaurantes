import { useCallback, useSyncExternalStore } from 'react'

export const PAGINAS = {
  inicio: 'Início',
  despesas: 'Despesas',
  contas: 'Contas a pagar',
  documentos: 'Documentos',
  fornecedores: 'Fornecedores',
  categorias: 'Categorias',
  assistente: 'Assistente',
} as const

export type Pagina = keyof typeof PAGINAS

function paginaAtual(): Pagina {
  const nome = window.location.hash.replace(/^#\/?/, '')
  return nome in PAGINAS ? (nome as Pagina) : 'inicio'
}

function assinar(aoMudar: () => void) {
  window.addEventListener('hashchange', aoMudar)
  return () => window.removeEventListener('hashchange', aoMudar)
}

/**
 * Navegação pelo trecho "#/pagina" do endereço: os botões Voltar/Avançar do navegador
 * funcionam e a página atual sobrevive a um recarregamento, sem biblioteca de rotas.
 */
export function useNavegacao() {
  const pagina = useSyncExternalStore(assinar, paginaAtual)
  const irPara = useCallback((destino: Pagina) => {
    window.location.hash = `/${destino}`
  }, [])
  return { pagina, irPara }
}
