import { describe, expect, it } from 'vitest'
import { formatarData, formatarDocumento, formatarMoeda, mesDe, valorParaApi, valorParaCampo } from './formato'

describe('valorParaApi', () => {
  it.each([
    ['1234,5', '1234.50'],
    ['1.234,56', '1234.56'],
    ['R$ 1.234,56', '1234.56'],
    ['1234.56', '1234.56'],
    ['0,10', '0.10'],
    ['  15 ', '15.00'],
    ['007', '7.00'],
  ])('converte "%s" em "%s"', (digitado, esperado) => {
    expect(valorParaApi(digitado)).toBe(esperado)
  })

  it.each(['', 'abc', '0', '0,00', '-5', '1,234', '12,3,4', '1.234.56', '99999999999'])(
    'rejeita "%s"',
    (digitado) => {
      expect(valorParaApi(digitado)).toBeNull()
    },
  )
})

describe('formatação', () => {
  it('formata dinheiro em reais', () => {
    expect(formatarMoeda('3370.50')).toMatch(/^R\$\s3\.370,50$/)
  })

  it('formata datas sem mudar o dia por causa do fuso', () => {
    expect(formatarData('2026-10-01')).toBe('01/10/2026')
  })

  it('prepara o valor para o campo de edição', () => {
    expect(valorParaCampo('1234.50')).toBe('1234,50')
  })

  it('formata CPF e CNPJ', () => {
    expect(formatarDocumento('52998224725')).toBe('529.982.247-25')
    expect(formatarDocumento('11222333000181')).toBe('11.222.333/0001-81')
    expect(formatarDocumento(null)).toBe('')
  })

  it('calcula o primeiro e o último dia do mês', () => {
    expect(mesDe(new Date(2026, 1, 15))).toEqual({ de: '2026-02-01', ate: '2026-02-28' })
    expect(mesDe(new Date(2028, 1, 15))).toEqual({ de: '2028-02-01', ate: '2028-02-29' })
  })
})
