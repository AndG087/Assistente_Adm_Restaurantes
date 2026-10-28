import { comConsulta, requisitar } from '../api'
import type { FiltroSituacao, Referencia } from './financeiro'

export interface TotalMes {
  ano: number
  mes: number
  rotulo: string
  quantidade: number
  valor_total: string
}

export interface EvolucaoMensal {
  meses: TotalMes[]
  media_mensal: string
}

export interface TotalFornecedor {
  fornecedor: Referencia | null
  quantidade: number
  valor_total: string
}

const base = (restauranteId: number) => `/api/restaurantes/${restauranteId}/relatorios`

export function evolucaoMensal(restauranteId: number, meses = 12): Promise<EvolucaoMensal> {
  return requisitar(comConsulta(`${base(restauranteId)}/mensal`, { meses }))
}

export function totaisPorFornecedor(restauranteId: number, de: string, ate: string): Promise<TotalFornecedor[]> {
  return requisitar(comConsulta(`${base(restauranteId)}/fornecedores`, { de, ate }))
}

/** Endereços de download: o navegador envia o cookie de sessão e salva o arquivo. */
export function urlCsvDespesas(restauranteId: number, de: string, ate: string): string {
  return comConsulta(`${base(restauranteId)}/despesas.csv`, { de, ate })
}

export function urlCsvContas(restauranteId: number, situacao: FiltroSituacao, de?: string, ate?: string): string {
  return comConsulta(`${base(restauranteId)}/contas.csv`, { situacao, de, ate })
}
