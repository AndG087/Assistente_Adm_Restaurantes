import { comConsulta, enviarJson, requisitar } from '../api'

export interface Referencia {
  id: number
  nome: string
}

// Valores em dinheiro são texto com 2 casas ("1234.50"), exatamente como o backend calculou.
interface LancamentoBase {
  id: number
  descricao: string
  valor: string
  categoria: Referencia | null
  fornecedor: Referencia | null
  numero_documento: string | null
  observacoes: string | null
  criado_em: string
}

export interface Despesa extends LancamentoBase {
  data: string
  conta_pagar_id: number | null
}

export type SituacaoConta = 'paga' | 'vencida' | 'vence_hoje' | 'a_vencer'
export type FiltroSituacao = 'pendentes' | 'vencidas' | 'pagas' | 'todas'

export interface ContaPagar extends LancamentoBase {
  data_vencimento: string
  data_pagamento: string | null
  situacao: SituacaoConta
  despesa_id: number | null
}

export interface Lista<T> {
  itens: T[]
  total: number
  valor_total: string
}

/** Campos enviados ao criar ou editar uma despesa ou conta. */
export interface DadosLancamento {
  descricao: string
  valor: string
  categoria_id: number | null
  fornecedor_id: number | null
  numero_documento: string | null
  observacoes: string | null
}

export interface ResumoDespesas {
  quantidade: number
  valor_total: string
  por_categoria: { categoria: Referencia | null; quantidade: number; valor_total: string }[]
}

export interface Alertas {
  hoje: string
  dias: number
  vencidas: { quantidade: number; valor_total: string }
  vencem_hoje: { quantidade: number; valor_total: string }
  proximos_dias: { quantidade: number; valor_total: string }
}

export interface FiltrosDespesas {
  de?: string
  ate?: string
  categoria_id?: number | null
  sem_categoria?: boolean
  busca?: string
  limite?: number
  deslocamento?: number
}

export interface FiltrosContas {
  situacao?: FiltroSituacao
  de?: string
  ate?: string
  busca?: string
  limite?: number
  deslocamento?: number
}

const despesas = (restauranteId: number) => `/api/restaurantes/${restauranteId}/despesas`
const contas = (restauranteId: number) => `/api/restaurantes/${restauranteId}/contas-a-pagar`

// --- Despesas ---

export function listarDespesas(restauranteId: number, filtros: FiltrosDespesas): Promise<Lista<Despesa>> {
  return requisitar(comConsulta(despesas(restauranteId), { ...filtros }))
}

export function resumoDespesas(restauranteId: number, de?: string, ate?: string): Promise<ResumoDespesas> {
  return requisitar(comConsulta(`${despesas(restauranteId)}/resumo`, { de, ate }))
}

export function salvarDespesa(
  restauranteId: number,
  id: number | null,
  dados: DadosLancamento & { data: string },
): Promise<Despesa> {
  return id === null
    ? requisitar(despesas(restauranteId), enviarJson('POST', dados))
    : requisitar(`${despesas(restauranteId)}/${id}`, enviarJson('PUT', dados))
}

export function excluirDespesa(restauranteId: number, id: number): Promise<void> {
  return requisitar(`${despesas(restauranteId)}/${id}`, { method: 'DELETE' })
}

// --- Contas a pagar ---

export function listarContas(restauranteId: number, filtros: FiltrosContas): Promise<Lista<ContaPagar>> {
  return requisitar(comConsulta(contas(restauranteId), { ...filtros }))
}

export function buscarAlertas(restauranteId: number, dias = 7): Promise<Alertas> {
  return requisitar(comConsulta(`${contas(restauranteId)}/alertas`, { dias }))
}

export function salvarConta(
  restauranteId: number,
  id: number | null,
  dados: DadosLancamento & { data_vencimento: string },
): Promise<ContaPagar> {
  return id === null
    ? requisitar(contas(restauranteId), enviarJson('POST', dados))
    : requisitar(`${contas(restauranteId)}/${id}`, enviarJson('PUT', dados))
}

export function excluirConta(restauranteId: number, id: number): Promise<void> {
  return requisitar(`${contas(restauranteId)}/${id}`, { method: 'DELETE' })
}

export function pagarConta(restauranteId: number, id: number, dataPagamento: string): Promise<ContaPagar> {
  return requisitar(`${contas(restauranteId)}/${id}/pagar`, enviarJson('POST', { data_pagamento: dataPagamento }))
}

export function desfazerPagamento(restauranteId: number, id: number): Promise<ContaPagar> {
  return requisitar(`${contas(restauranteId)}/${id}/desfazer-pagamento`, { method: 'POST' })
}
