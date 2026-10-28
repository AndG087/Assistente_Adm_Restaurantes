import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { chamadas, corpoEnviado, json, renderizarNaArea, simularBackend } from '../test/backendFalso'
import { ContasPagar } from './ContasPagar'

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

describe('Contas a pagar', () => {
  it('mostra pendentes com a situação de cada uma', async () => {
    const fetchFalso = simularBackend({
      'GET /api/restaurantes/10/contas-a-pagar': () =>
        json({
          itens: [conta({}), conta({ id: 2, descricao: 'Energia', situacao: 'vence_hoje', valor: '800.40' })],
          total: 2,
          valor_total: '1180.40',
        }),
    })

    renderizarNaArea(<ContasPagar />)

    const gas = (await screen.findByText('Boleto do gás')).closest('tr')!
    expect(within(gas).getByText('Vencida')).toBeInTheDocument()
    const energia = screen.getByText('Energia').closest('tr')!
    expect(within(energia).getByText('Vence hoje')).toBeInTheDocument()
    expect(screen.getByText(/R\$\s1\.180,40/)).toBeInTheDocument()
    expect(chamadas(fetchFalso, 'GET', '/api/restaurantes/10/contas-a-pagar')[0].url.searchParams.get('situacao')).toBe(
      'pendentes',
    )
  })

  it('troca a aba de situação', async () => {
    const fetchFalso = simularBackend({
      'GET /api/restaurantes/10/contas-a-pagar': () => json({ itens: [], total: 0, valor_total: '0.00' }),
    })
    renderizarNaArea(<ContasPagar />)
    await screen.findByText('Nenhuma conta nesta situação.')

    await userEvent.click(screen.getByRole('button', { name: 'Pagas' }))

    expect(screen.getByRole('button', { name: 'Pagas' })).toHaveAttribute('aria-pressed', 'true')
    await waitFor(() =>
      expect(
        chamadas(fetchFalso, 'GET', '/api/restaurantes/10/contas-a-pagar').at(-1)!.url.searchParams.get('situacao'),
      ).toBe('pagas'),
    )
  })

  it('registra o pagamento com a data escolhida', async () => {
    const fetchFalso = simularBackend({
      'GET /api/restaurantes/10/contas-a-pagar': () => json({ itens: [conta({})], total: 1, valor_total: '380.00' }),
      'POST /api/restaurantes/10/contas-a-pagar/1/pagar': () =>
        json(conta({ situacao: 'paga', data_pagamento: '2026-10-18', despesa_id: 9 })),
    })
    renderizarNaArea(<ContasPagar />)

    await userEvent.click(await screen.findByRole('button', { name: 'Pagar Boleto do gás' }))
    const dialogo = screen.getByRole('dialog', { name: 'Confirmar pagamento' })
    expect(dialogo).toHaveTextContent('Uma despesa será criada automaticamente')
    const campoData = within(dialogo).getByLabelText('Data do pagamento')
    await userEvent.clear(campoData)
    await userEvent.type(campoData, '2026-10-18')
    await userEvent.click(within(dialogo).getByRole('button', { name: 'Confirmar pagamento' }))

    await waitFor(() => expect(chamadas(fetchFalso, 'POST', '/api/restaurantes/10/contas-a-pagar/1/pagar')).toHaveLength(1))
    expect(corpoEnviado(chamadas(fetchFalso, 'POST', '/api/restaurantes/10/contas-a-pagar/1/pagar')[0])).toEqual({
      data_pagamento: '2026-10-18',
    })
    await waitFor(() => expect(chamadas(fetchFalso, 'GET', '/api/restaurantes/10/contas-a-pagar')).toHaveLength(2))
  })

  it('conta paga só oferece desfazer o pagamento', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    const fetchFalso = simularBackend({
      'GET /api/restaurantes/10/contas-a-pagar': () =>
        json({
          itens: [conta({ situacao: 'paga', data_pagamento: '2026-10-18', despesa_id: 9 })],
          total: 1,
          valor_total: '380.00',
        }),
      'POST /api/restaurantes/10/contas-a-pagar/1/desfazer-pagamento': () => json(conta({})),
    })
    renderizarNaArea(<ContasPagar />)

    expect(await screen.findByText('em 18/10/2026')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Editar Boleto do gás' })).not.toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Desfazer pagamento de Boleto do gás' }))

    await waitFor(() =>
      expect(chamadas(fetchFalso, 'POST', '/api/restaurantes/10/contas-a-pagar/1/desfazer-pagamento')).toHaveLength(1),
    )
  })

  it('mostra o erro do backend ao pagar', async () => {
    simularBackend({
      'GET /api/restaurantes/10/contas-a-pagar': () => json({ itens: [conta({})], total: 1, valor_total: '380.00' }),
      'POST /api/restaurantes/10/contas-a-pagar/1/pagar': () =>
        json({ detail: 'A data de pagamento não pode estar no futuro.' }, 409),
    })
    renderizarNaArea(<ContasPagar />)

    await userEvent.click(await screen.findByRole('button', { name: 'Pagar Boleto do gás' }))
    await userEvent.click(screen.getByRole('button', { name: 'Confirmar pagamento' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('A data de pagamento não pode estar no futuro.')
  })

  it('não deixa confirmar o pagamento com a data vazia', async () => {
    const fetchFalso = simularBackend({
      'GET /api/restaurantes/10/contas-a-pagar': () => json({ itens: [conta({})], total: 1, valor_total: '380.00' }),
    })
    renderizarNaArea(<ContasPagar />)

    await userEvent.click(await screen.findByRole('button', { name: 'Pagar Boleto do gás' }))
    const dialogo = screen.getByRole('dialog', { name: 'Confirmar pagamento' })
    await userEvent.clear(within(dialogo).getByLabelText('Data do pagamento'))

    expect(within(dialogo).getByRole('button', { name: 'Confirmar pagamento' })).toBeDisabled()
    expect(dialogo).toHaveTextContent('Informe a data do pagamento.')
    expect(chamadas(fetchFalso, 'POST', '/api/restaurantes/10/contas-a-pagar/1/pagar')).toHaveLength(0)
  })

  it('traduz o erro de validação do backend dizendo qual campo', async () => {
    simularBackend({
      'GET /api/restaurantes/10/contas-a-pagar': () => json({ itens: [conta({})], total: 1, valor_total: '380.00' }),
      'POST /api/restaurantes/10/contas-a-pagar/1/pagar': () =>
        json(
          { detail: [{ loc: ['body', 'data_pagamento'], msg: 'Input should be a valid date or datetime, input is too short' }] },
          422,
        ),
    })
    renderizarNaArea(<ContasPagar />)

    await userEvent.click(await screen.findByRole('button', { name: 'Pagar Boleto do gás' }))
    await userEvent.click(screen.getByRole('button', { name: 'Confirmar pagamento' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Data de pagamento precisa ser uma data válida.')
  })
})
