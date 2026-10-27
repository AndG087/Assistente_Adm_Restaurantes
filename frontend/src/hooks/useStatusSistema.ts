import { useCallback, useEffect, useState } from 'react'
import { buscarSaude, buscarStatusIA, type HealthResponse, type IAStatusResponse } from '../api'

export interface StatusSistema {
  carregando: boolean
  backend: HealthResponse | null
  ia: IAStatusResponse | null
  atualizar: () => void
}

interface ResultadoStatus {
  backend: HealthResponse | null
  ia: IAStatusResponse | null
}

// Uma falha não impede a outra: o backend pode responder mesmo com a IA desligada.
async function consultarStatus(): Promise<ResultadoStatus> {
  const [saude, statusIa] = await Promise.allSettled([buscarSaude(), buscarStatusIA()])
  return {
    backend: saude.status === 'fulfilled' ? saude.value : null,
    ia: statusIa.status === 'fulfilled' ? statusIa.value : null,
  }
}

export function useStatusSistema(): StatusSistema {
  const [carregando, setCarregando] = useState(true)
  const [resultado, setResultado] = useState<ResultadoStatus>({ backend: null, ia: null })
  // Incrementar este número dispara uma nova verificação.
  const [versao, setVersao] = useState(0)

  useEffect(() => {
    let ativo = true
    consultarStatus().then((novo) => {
      if (!ativo) return
      setResultado(novo)
      setCarregando(false)
    })
    return () => {
      ativo = false
    }
  }, [versao])

  const atualizar = useCallback(() => {
    setCarregando(true)
    setVersao((v) => v + 1)
  }, [])

  return { carregando, backend: resultado.backend, ia: resultado.ia, atualizar }
}
