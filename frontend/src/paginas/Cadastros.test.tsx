import { fireEvent, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { chamadas, corpoEnviado, json, renderizarNaArea, simularBackend } from '../test/backendFalso'
import { Categorias } from './Categorias'
import { Fornecedores } from './Fornecedores'
import { Inicio } from './Inicio'

describe('Fornecedores', () => {
  it('lista com documento formatado e cadastra um novo', async () => {
    const fetchFalso = simularBackend({
      'GET /api/restaurantes/10/fornecedores': () =>
        json([
          {
            id: 1,
            nome: 'Distribuidora Sul',
            documento: '11222333000181',
            telefone: '(11) 98765-4321',
            email: null,
            observacoes: null,
            ativo: true,
          },
        ]),
      'POST /api/restaurantes/10/fornecedores': () => json({ id: 2 }, 201),
    })
    renderizarNaArea(<Fornecedores />)

    expect(await screen.findByText('11.222.333/0001-81')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Novo fornecedor' }))
    await userEvent.type(screen.getByLabelText('Nome'), 'Feira do Zé')
    await userEvent.type(screen.getByLabelText('CPF ou CNPJ (opcional)'), '529.982.247-25')
    await userEvent.click(screen.getByRole('button', { name: 'Salvar' }))

    await screen.findByRole('heading', { name: 'Fornecedores' })
    expect(corpoEnviado(chamadas(fetchFalso, 'POST', '/api/restaurantes/10/fornecedores')[0])).toEqual({
      nome: 'Feira do Zé',
      documento: '529.982.247-25',
      telefone: '',
      email: '',
      observacoes: '',
    })
  })

  it('mostra o erro de documento repetido', async () => {
    simularBackend({
      'GET /api/restaurantes/10/fornecedores': () => json([]),
      'POST /api/restaurantes/10/fornecedores': () =>
        json({ detail: 'Já existe um fornecedor com este CPF/CNPJ neste restaurante.' }, 409),
    })
    renderizarNaArea(<Fornecedores />)

    await userEvent.click(await screen.findByRole('button', { name: 'Novo fornecedor' }))
    await userEvent.type(screen.getByLabelText('Nome'), 'Repetido')
    await userEvent.click(screen.getByRole('button', { name: 'Salvar' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Já existe um fornecedor com este CPF/CNPJ')
  })
})

describe('Categorias', () => {
  it('cria, renomeia e inativa', async () => {
    const fetchFalso = simularBackend({
      'GET /api/restaurantes/10/categorias': () => json([{ id: 1, nome: 'Bebidas', ativo: true }]),
      'POST /api/restaurantes/10/categorias': () => json({ id: 2, nome: 'Eventos', ativo: true }, 201),
      'PUT /api/restaurantes/10/categorias/1': () => json({ id: 1, nome: 'Bebidas e sucos', ativo: true }),
    })
    renderizarNaArea(<Categorias />)

    await userEvent.type(await screen.findByLabelText('Nova categoria'), 'Eventos')
    await userEvent.click(screen.getByRole('button', { name: 'Adicionar' }))
    await waitFor(() => expect(chamadas(fetchFalso, 'POST', '/api/restaurantes/10/categorias')).toHaveLength(1))
    expect(screen.getByLabelText('Nova categoria')).toHaveValue('')

    await userEvent.click(screen.getByRole('button', { name: 'Renomear Bebidas' }))
    const campo = screen.getByLabelText('Novo nome para Bebidas')
    await userEvent.clear(campo)
    await userEvent.type(campo, 'Bebidas e sucos{Enter}')
    await waitFor(() => expect(chamadas(fetchFalso, 'PUT', '/api/restaurantes/10/categorias/1')).toHaveLength(1))
    expect(corpoEnviado(chamadas(fetchFalso, 'PUT', '/api/restaurantes/10/categorias/1')[0])).toEqual({
      nome: 'Bebidas e sucos',
      ativo: true,
    })

    await userEvent.click(await screen.findByRole('button', { name: 'Inativar Bebidas' }))
    await waitFor(() => expect(chamadas(fetchFalso, 'PUT', '/api/restaurantes/10/categorias/1')).toHaveLength(2))
    expect(corpoEnviado(chamadas(fetchFalso, 'PUT', '/api/restaurantes/10/categorias/1')[1])).toEqual({
      nome: 'Bebidas',
      ativo: false,
    })
  })

  it('clique duplo envia o pedido uma vez só e trava o botão até a resposta', async () => {
    let responder: (r: Response) => void = () => {}
    const fetchFalso = simularBackend({
      'GET /api/restaurantes/10/categorias': () => json([{ id: 1, nome: 'Bebidas', ativo: true }]),
      'PUT /api/restaurantes/10/categorias/1': () => new Promise<Response>((r) => (responder = r)),
    })
    renderizarNaArea(<Categorias />)

    const botao = await screen.findByRole('button', { name: 'Inativar Bebidas' })
    fireEvent.click(botao)
    fireEvent.click(botao) // mesmo instante: a tela ainda não foi redesenhada

    await waitFor(() => expect(botao).toBeDisabled())
    expect(chamadas(fetchFalso, 'PUT', '/api/restaurantes/10/categorias/1')).toHaveLength(1)
    responder(json({ id: 1, nome: 'Bebidas', ativo: false }))
    await waitFor(() => expect(botao).toBeEnabled())
  })
})

describe('Início', () => {
  it('mostra alertas e despesas do mês vindos do backend', async () => {
    simularBackend({
      'GET /api/restaurantes/10/contas-a-pagar/alertas': () =>
        json({
          hoje: '2026-10-20',
          dias: 7,
          vencidas: { quantidade: 2, valor_total: '3500.00' },
          vencem_hoje: { quantidade: 1, valor_total: '800.40' },
          proximos_dias: { quantidade: 0, valor_total: '0.00' },
        }),
      'GET /api/restaurantes/10/despesas/resumo': () =>
        json({
          quantidade: 3,
          valor_total: '2920.00',
          por_categoria: [
            { categoria: { id: 1, nome: 'Aluguel' }, quantidade: 1, valor_total: '2500.00' },
            { categoria: null, quantidade: 2, valor_total: '420.00' },
          ],
        }),
    })

    const irPara = vi.fn()
    renderizarNaArea(<Inicio irPara={irPara} />)

    expect(await screen.findByText(/R\$\s3\.500,00/)).toBeInTheDocument()
    expect(screen.getByText('2 contas')).toBeInTheDocument()
    expect(screen.getByText('Nenhuma conta')).toBeInTheDocument()
    expect(screen.getByText(/R\$\s2\.920,00/)).toBeInTheDocument()
    expect(screen.getByText('Sem categoria')).toBeInTheDocument()
    // Participação de cada categoria no total, calculada dos próprios valores: 2500 / 2920 e 420 / 2920.
    const categorias = screen.getByRole('list', { name: 'Despesas por categoria' })
    expect(categorias).toHaveTextContent('85,6%')
    expect(categorias).toHaveTextContent('14,4%')

    await userEvent.click(screen.getByRole('button', { name: /Vencidas/ }))
    expect(irPara).toHaveBeenCalledWith('contas')
  })
})
