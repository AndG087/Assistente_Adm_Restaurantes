import { comConsulta, requisitar } from '../api'

export type StatusDocumento = 'pendente' | 'concluido' | 'descartado' | 'erro'

/** Campos encontrados no texto por regras fixas (sugestões para a conferência). */
export interface DadosExtraidos {
  valor: string | null
  data_emissao: string | null
  data_vencimento: string | null
  cnpj_emitente: string | null
  numero_documento: string | null
  chave_acesso: string | null
  tipo_sugerido: 'despesa' | 'conta' | null
}

export interface Documento {
  id: number
  nome_original: string
  tipo_mime: string
  tamanho_bytes: number
  status: StatusDocumento
  metodo_extracao: 'pdf_texto' | 'ocr' | null
  erro: string | null
  dados_extraidos: DadosExtraidos | null
  despesa_id: number | null
  conta_pagar_id: number | null
  criado_em: string
}

export interface DocumentoDetalhe extends Documento {
  texto_extraido: string | null
}

const base = (restauranteId: number) => `/api/restaurantes/${restauranteId}/documentos`

export function listarDocumentos(restauranteId: number, status: StatusDocumento | null): Promise<Documento[]> {
  return requisitar(comConsulta(base(restauranteId), { status }))
}

export function obterDocumento(restauranteId: number, id: number): Promise<DocumentoDetalhe> {
  return requisitar(`${base(restauranteId)}/${id}`)
}

export function enviarDocumento(restauranteId: number, arquivo: File): Promise<DocumentoDetalhe> {
  const formulario = new FormData()
  formulario.append('arquivo', arquivo)
  return requisitar(base(restauranteId), { method: 'POST', body: formulario })
}

export function reprocessarDocumento(restauranteId: number, id: number): Promise<DocumentoDetalhe> {
  return requisitar(`${base(restauranteId)}/${id}/reprocessar`, { method: 'POST' })
}

export function excluirDocumento(restauranteId: number, id: number): Promise<void> {
  return requisitar(`${base(restauranteId)}/${id}`, { method: 'DELETE' })
}

export function urlDoArquivo(restauranteId: number, id: number): string {
  return `${base(restauranteId)}/${id}/arquivo`
}
