import { useCallback, useState } from 'react'

export type Tema = 'claro' | 'escuro'

/** Mesma chave lida pelo script do index.html, que aplica o tema antes de o React desenhar a tela. */
export const CHAVE_TEMA = 'caderninho-tema'

function temaSalvo(): Tema {
  try {
    return localStorage.getItem(CHAVE_TEMA) === 'escuro' ? 'escuro' : 'claro'
  } catch {
    // Navegador com armazenamento bloqueado (ex.: janela anônima restrita): fica no claro.
    return 'claro'
  }
}

function aplicar(tema: Tema) {
  if (tema === 'escuro') document.documentElement.dataset.tema = 'escuro'
  else delete document.documentElement.dataset.tema
}

/** Tema claro por padrão, igual para todo mundo; o escuro só quando a pessoa escolhe. */
export function useTema() {
  const [tema, setTema] = useState<Tema>(() => {
    const inicial = temaSalvo()
    aplicar(inicial)
    return inicial
  })

  const alternar = useCallback(() => {
    const novo: Tema = tema === 'escuro' ? 'claro' : 'escuro'
    aplicar(novo)
    try {
      localStorage.setItem(CHAVE_TEMA, novo)
    } catch {
      // Sem armazenamento, a escolha vale só até recarregar a página.
    }
    setTema(novo)
  }, [tema])

  return { tema, alternar }
}
