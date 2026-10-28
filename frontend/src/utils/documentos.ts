import type { StatusDocumento } from '../recursos/documentos'

/** Nome de cada situação de documento, como aparece nas telas. */
export const STATUS: Record<StatusDocumento, string> = {
  pendente: 'A conferir',
  erro: 'Erro na leitura',
  concluido: 'Conferido',
  descartado: 'Descartado',
}
