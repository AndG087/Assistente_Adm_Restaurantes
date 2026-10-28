import { enviarJson, requisitar } from '../api'

export type Papel = 'proprietario' | 'membro'

export interface Membro {
  usuario_id: number
  nome: string
  email: string
  papel: Papel
  voce: boolean
}

const base = (restauranteId: number) => `/api/restaurantes/${restauranteId}/membros`

export function listarMembros(restauranteId: number): Promise<Membro[]> {
  return requisitar(base(restauranteId))
}

export function adicionarMembro(restauranteId: number, email: string, papel: Papel): Promise<Membro> {
  return requisitar(base(restauranteId), enviarJson('POST', { email, papel }))
}

export function alterarPapel(restauranteId: number, usuarioId: number, papel: Papel): Promise<Membro> {
  return requisitar(`${base(restauranteId)}/${usuarioId}`, enviarJson('PUT', { papel }))
}

export function removerMembro(restauranteId: number, usuarioId: number): Promise<void> {
  return requisitar(`${base(restauranteId)}/${usuarioId}`, { method: 'DELETE' })
}
