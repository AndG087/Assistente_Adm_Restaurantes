import { describe, expect, it } from 'vitest'
import {
  formatarData,
  formatarDocumento,
  formatarMoeda,
  mesDe,
  periodosComparaveis,
  valorParaApi,
  valorParaCampo,
} from './formato'

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

describe('periodosComparaveis', () => {
  it.each([
    // [hoje, este mês até hoje, mesmo pedaço do mês anterior]
    ['dia comum', new Date(2026, 9, 28), ['2026-10-01', '2026-10-28'], ['2026-09-01', '2026-09-28']],
    ['dia 31 com mês anterior de 30 dias', new Date(2026, 9, 31), ['2026-10-01', '2026-10-31'], ['2026-09-01', '2026-09-30']],
    ['março depois de fevereiro comum', new Date(2027, 2, 31), ['2027-03-01', '2027-03-31'], ['2027-02-01', '2027-02-28']],
    ['março depois de fevereiro bissexto', new Date(2028, 2, 30), ['2028-03-01', '2028-03-30'], ['2028-02-01', '2028-02-29']],
    ['janeiro compara com dezembro do ano anterior', new Date(2027, 0, 15), ['2027-01-01', '2027-01-15'], ['2026-12-01', '2026-12-15']],
    ['primeiro dia do mês', new Date(2026, 10, 1), ['2026-11-01', '2026-11-01'], ['2026-10-01', '2026-10-01']],
  ])('%s', (_caso, hoje, [deAtual, ateAtual], [deAnterior, ateAnterior]) => {
    expect(periodosComparaveis(hoje)).toEqual({
      atual: { de: deAtual, ate: ateAtual },
      anterior: { de: deAnterior, ate: ateAnterior },
    })
  })
})
