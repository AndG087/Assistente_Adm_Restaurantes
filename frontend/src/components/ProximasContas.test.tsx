import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { chamadas, corpoEnviado, json, renderizarNaArea, simularBackend } from '../test/backendFalso'
import { hojeIso } from '../utils/formato'
import { ProximasContas } from './ProximasContas'

function conta(campos: Record<string, unknown>) {
  return {
    id: 1,
    descricao: 'Boleto do gás',
    valor: '380.00',
    data_vencimento: '2026-10-19',
    data_pagamento: null,
    situacao: 'vencida',
    categoria: null,
    fornecedor: null,
    numero_documento: null,
    observacoes: null,
    despesa_id: null,
    criado_em: '2026-10-01T12:00:00',
    ...campos,
  }
}

const URL_CONTAS = '/api/restaurantes/10/contas-a-pagar'

describe('Próximas contas', () => {
  it('lista as pendentes e avisa quantas ficaram de fora', async () => {
    const fetchFalso = simularBackend({
      [`GET ${URL_CONTAS}`]: () =>
        json({ itens: [conta({}), conta({ id: 2, descricao: 'Energia', situacao: 'a_vencer' })], total: 7, valor_total: '1' }),
    })
    renderizarNaArea(<ProximasContas onPagamento={() => {}} onVerTodas={() => {}} />)

    expect(await screen.findByText('Boleto do gás')).toBeInTheDocument()
    expect(screen.getByText('Energia')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Ver todas as contas (+5)' })).toBeInTheDocument()
    const [pedido] = chamadas(fetchFalso, 'GET', URL_CONTAS)
    expect(pedido.url.searchParams.get('situacao')).toBe('pendentes')
    expect(pedido.url.searchParams.get('limite')).toBe('5')
  })

  it('paga com a data de hoje só depois de confirmar', async () => {
    const onPagamento = vi.fn()
    const fetchFalso = simularBackend({
      [`GET ${URL_CONTAS}`]: () => json({ itens: [conta({})], total: 1, valor_total: '380.00' }),
      [`POST ${URL_CONTAS}/1/pagar`]: () => json(conta({ situacao: 'paga', data_pagamento: hojeIso() })),
    })
    renderizarNaArea(<ProximasContas onPagamento={onPagamento} onVerTodas={() => {}} />)

    await userEvent.click(await screen.findByRole('button', { name: 'Pagar Boleto do gás' }))
    expect(chamadas(fetchFalso, 'POST', `${URL_CONTAS}/1/pagar`)).toHaveLength(0)

    const confirmacao = screen.getByRole('group', { name: 'Confirmar pagamento de Boleto do gás' })
    expect(confirmacao).toHaveTextContent('Pagar hoje?')
    await userEvent.click(within(confirmacao).getByRole('button', { name: 'Confirmar' }))

    await waitFor(() => expect(onPagamento).toHaveBeenCalledTimes(1))
    const [pagamento] = chamadas(fetchFalso, 'POST', `${URL_CONTAS}/1/pagar`)
    expect(corpoEnviado(pagamento)).toEqual({ data_pagamento: hojeIso() })
    // A lista é recarregada para tirar a conta paga.
    expect(chamadas(fetchFalso, 'GET', URL_CONTAS)).toHaveLength(2)
  })

  it('cancelar não paga', async () => {
    const fetchFalso = simularBackend({
      [`GET ${URL_CONTAS}`]: () => json({ itens: [conta({})], total: 1, valor_total: '380.00' }),
    })
    renderizarNaArea(<ProximasContas onPagamento={() => {}} onVerTodas={() => {}} />)

    await userEvent.click(await screen.findByRole('button', { name: 'Pagar Boleto do gás' }))
    await userEvent.click(screen.getByRole('button', { name: 'Cancelar' }))

    expect(screen.getByRole('button', { name: 'Pagar Boleto do gás' })).toBeInTheDocument()
    expect(chamadas(fetchFalso, 'POST', `${URL_CONTAS}/1/pagar`)).toHaveLength(0)
  })

  it('sem pendências, diz que está tudo em dia', async () => {
    simularBackend({ [`GET ${URL_CONTAS}`]: () => json({ itens: [], total: 0, valor_total: '0' }) })
    renderizarNaArea(<ProximasContas onPagamento={() => {}} onVerTodas={() => {}} />)

    expect(await screen.findByText('Nenhuma conta pendente. Tudo em dia!')).toBeInTheDocument()
  })
})
