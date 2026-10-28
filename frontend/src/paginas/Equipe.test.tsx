import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { chamadas, corpoEnviado, json, RESTAURANTE, renderizarNaArea, semConteudo, simularBackend } from '../test/backendFalso'
import { Equipe } from './Equipe'

const ANA = { usuario_id: 1, nome: 'Ana Souza', email: 'ana@exemplo.com', papel: 'proprietario', voce: true }
const BRUNO = { usuario_id: 2, nome: 'Bruno Lima', email: 'bruno@exemplo.com', papel: 'membro', voce: false }

describe('Equipe', () => {
  it('proprietário adiciona uma pessoa pelo e-mail', async () => {
    const fetchFalso = simularBackend({
      'GET /api/restaurantes/10/membros': () => json([ANA]),
      'POST /api/restaurantes/10/membros': () => json(BRUNO, 201),
    })
    renderizarNaArea(<Equipe />)

    await userEvent.type(await screen.findByLabelText('E-mail da pessoa'), 'bruno@exemplo.com')
    await userEvent.click(screen.getByRole('button', { name: 'Adicionar' }))

    await waitFor(() => expect(chamadas(fetchFalso, 'POST', '/api/restaurantes/10/membros')).toHaveLength(1))
    expect(corpoEnviado(chamadas(fetchFalso, 'POST', '/api/restaurantes/10/membros')[0])).toEqual({
      email: 'bruno@exemplo.com',
      papel: 'membro',
    })
    expect(screen.getByLabelText('E-mail da pessoa')).toHaveValue('')
  })

  it('mostra o motivo quando não é possível mudar o papel', async () => {
    simularBackend({
      'GET /api/restaurantes/10/membros': () => json([ANA]),
      'PUT /api/restaurantes/10/membros/1': () =>
        json({ detail: 'O restaurante precisa de pelo menos um proprietário. Promova outra pessoa antes.' }, 409),
    })
    renderizarNaArea(<Equipe />)

    await userEvent.selectOptions(await screen.findByLabelText('Papel de Ana Souza'), 'Membro')

    expect(await screen.findByRole('alert')).toHaveTextContent('pelo menos um proprietário')
  })

  it('membro só vê a equipe e pode sair', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    simularBackend({
      'GET /api/restaurantes/10/membros': () =>
        json([{ ...ANA, voce: false }, { ...BRUNO, voce: true }]),
      'DELETE /api/restaurantes/10/membros/2': semConteudo,
    })
    const { recarregarRestaurantes } = renderizarNaArea(<Equipe />, { ...RESTAURANTE, papel: 'membro' })

    await screen.findByText('Bruno Lima')
    expect(screen.queryByLabelText('E-mail da pessoa')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Remover Ana Souza' })).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Sair do restaurante' }))

    await waitFor(() => expect(recarregarRestaurantes).toHaveBeenCalled())
  })
})
