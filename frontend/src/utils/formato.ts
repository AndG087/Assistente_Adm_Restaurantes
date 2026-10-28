// Formatação para exibição e conversão de valores digitados pelo usuário.
// Os valores em dinheiro chegam da API como texto ("1234.50") e nunca passam por soma no frontend:
// totais vêm sempre calculados pelo backend.

const MOEDA = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })

export function formatarMoeda(valor: string | number): string {
  return MOEDA.format(Number(valor))
}

/** "2026-10-05" → "05/10/2026" (sem passar por Date, que poderia mudar o dia por causa do fuso). */
export function formatarData(iso: string): string {
  const [ano, mes, dia] = iso.split('-')
  return `${dia}/${mes}/${ano}`
}

/** Valor para preencher o campo de edição: "1234.50" → "1234,50". */
export function valorParaCampo(valor: string): string {
  return valor.replace('.', ',')
}

/**
 * Converte o que o usuário digitou no formato da API, ou null se for inválido.
 * Aceita "1234,5", "1.234,56", "R$ 1.234,56" e também "1234.56".
 */
export function valorParaApi(digitado: string): string | null {
  let texto = digitado.replace(/R\$/i, '').replace(/\s/g, '')
  if (texto.includes(',')) {
    // Formato brasileiro: ponto separa milhares, vírgula separa centavos.
    texto = texto.replace(/\./g, '').replace(',', '.')
  }
  if (!/^\d{1,10}(\.\d{1,2})?$/.test(texto)) return null
  const [inteiro, decimais = ''] = texto.split('.')
  const resultado = `${Number(inteiro)}.${decimais.padEnd(2, '0')}`
  return Number(resultado) > 0 ? resultado : null
}

export function formatarDocumento(digitos: string | null): string {
  if (!digitos) return ''
  if (digitos.length === 11) return digitos.replace(/^(\d{3})(\d{3})(\d{3})(\d{2})$/, '$1.$2.$3-$4')
  if (digitos.length === 14) return digitos.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/, '$1.$2.$3/$4-$5')
  return digitos
}

function paraIso(data: Date): string {
  const mes = String(data.getMonth() + 1).padStart(2, '0')
  const dia = String(data.getDate()).padStart(2, '0')
  return `${data.getFullYear()}-${mes}-${dia}`
}

/** Data de hoje no fuso do computador, no formato da API. */
export function hojeIso(): string {
  return paraIso(new Date())
}

/** Primeiro e último dia do mês da data informada. */
export function mesDe(referencia = new Date()): { de: string; ate: string } {
  const inicio = new Date(referencia.getFullYear(), referencia.getMonth(), 1)
  const fim = new Date(referencia.getFullYear(), referencia.getMonth() + 1, 0)
  return { de: paraIso(inicio), ate: paraIso(fim) }
}
