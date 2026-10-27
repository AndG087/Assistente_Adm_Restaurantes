import { useCallback, useEffect, useState } from 'react'
import { ApiError, buscarUsuarioAtual, cadastrar, entrar, sair, type Usuario } from '../api'

export interface Sessao {
  // true enquanto ainda não se sabe se há uma sessão aberta
  verificando: boolean
  usuario: Usuario | null
  // Erro ao verificar a sessão que não seja "não logado" (ex.: backend fora do ar)
  erroVerificacao: string | null
  entrar: (email: string, senha: string) => Promise<void>
  cadastrar: (nome: string, email: string, senha: string) => Promise<void>
  sair: () => Promise<void>
  // Chamado quando alguma requisição responde 401 (sessão expirada)
  sessaoExpirou: () => void
  tentarNovamente: () => void
}

export function useSessao(): Sessao {
  const [verificando, setVerificando] = useState(true)
  const [usuario, setUsuario] = useState<Usuario | null>(null)
  const [erroVerificacao, setErroVerificacao] = useState<string | null>(null)
  const [tentativa, setTentativa] = useState(0)

  useEffect(() => {
    let ativo = true
    buscarUsuarioAtual()
      .then((u) => {
        if (!ativo) return
        setUsuario(u)
        setErroVerificacao(null)
      })
      .catch((erro: unknown) => {
        if (!ativo) return
        setUsuario(null)
        const naoLogado = erro instanceof ApiError && erro.status === 401
        setErroVerificacao(naoLogado ? null : erro instanceof Error ? erro.message : 'Erro inesperado.')
      })
      .finally(() => {
        if (ativo) setVerificando(false)
      })
    return () => {
      ativo = false
    }
  }, [tentativa])

  const tentarNovamente = useCallback(() => {
    setVerificando(true)
    setTentativa((t) => t + 1)
  }, [])

  const fazerLogin = useCallback(async (email: string, senha: string) => {
    setUsuario(await entrar(email, senha))
    setErroVerificacao(null)
  }, [])

  const fazerCadastro = useCallback(async (nome: string, email: string, senha: string) => {
    setUsuario(await cadastrar(nome, email, senha))
    setErroVerificacao(null)
  }, [])

  const fazerLogout = useCallback(async () => {
    try {
      await sair()
    } finally {
      setUsuario(null)
    }
  }, [])

  const sessaoExpirou = useCallback(() => setUsuario(null), [])

  return {
    verificando,
    usuario,
    erroVerificacao,
    entrar: fazerLogin,
    cadastrar: fazerCadastro,
    sair: fazerLogout,
    sessaoExpirou,
    tentarNovamente,
  }
}
