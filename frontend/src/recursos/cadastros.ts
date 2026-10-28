import { comConsulta, enviarJson, requisitar } from '../api'

export interface Fornecedor {
  id: number
  nome: string
  documento: string | null
  telefone: string | null
  email: string | null
  observacoes: string | null
  ativo: boolean
}

export type DadosFornecedor = Omit<Fornecedor, 'id'>

export interface Categoria {
  id: number
  nome: string
  ativo: boolean
}

const base = (restauranteId: number) => `/api/restaurantes/${restauranteId}`

export function listarFornecedores(
  restauranteId: number,
  filtros: { busca?: string; incluir_inativos?: boolean } = {},
): Promise<Fornecedor[]> {
  return requisitar(comConsulta(`${base(restauranteId)}/fornecedores`, filtros))
}

export function salvarFornecedor(restauranteId: number, id: number | null, dados: DadosFornecedor): Promise<Fornecedor> {
  const { ativo, ...campos } = dados
  return id === null
    ? requisitar(`${base(restauranteId)}/fornecedores`, enviarJson('POST', campos))
    : requisitar(`${base(restauranteId)}/fornecedores/${id}`, enviarJson('PUT', { ...campos, ativo }))
}

export function listarCategorias(restauranteId: number, incluirInativas = false): Promise<Categoria[]> {
  return requisitar(comConsulta(`${base(restauranteId)}/categorias`, { incluir_inativas: incluirInativas }))
}

export function criarCategoria(restauranteId: number, nome: string): Promise<Categoria> {
  return requisitar(`${base(restauranteId)}/categorias`, enviarJson('POST', { nome }))
}

export interface SugestaoCategoria {
  categoria: { id: number; nome: string } | null
  origem: 'palavra_chave' | 'historico' | 'ia' | null
  mensagem: string
}

export function sugerirCategoria(
  restauranteId: number,
  descricao: string,
  fornecedorId: number | null,
): Promise<SugestaoCategoria> {
  return requisitar(
    `${base(restauranteId)}/sugestoes/categoria`,
    enviarJson('POST', { descricao, fornecedor_id: fornecedorId }),
  )
}

export function atualizarCategoria(restauranteId: number, id: number, nome: string, ativo: boolean): Promise<Categoria> {
  return requisitar(`${base(restauranteId)}/categorias/${id}`, enviarJson('PUT', { nome, ativo }))
}
