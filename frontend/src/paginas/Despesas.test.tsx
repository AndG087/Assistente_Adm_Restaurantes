import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { chamadas, corpoEnviado, json, renderizarNaArea, semConteudo, simularBackend } from '../test/backendFalso'
import { Despesas } from './Despesas'

const DESPESA = {
  id: 1,
  descricao: 'Compra de legumes',
  valor: '1234.50',
  data: '2026-10-10',
  categoria: { id: 3, nome: 'Alimentos e insumos' },
  fornecedor: { id: 7, nome: 'Hortifruti Verde' },
  numero_documento: 'NF 4521',
  observacoes: null,
  conta_pagar_id: null,
  criado_em: '2026-10-10T12:00:00',
}

const OPCOES = {
  'GET /api/restaurantes/10/categorias': () =>
    json([
      { id: 3, nome: 'Alimentos e insumos', ativo: true },
      { id: 4, nome: 'Bebidas', ativo: true },
    ]),
  'GET /api/restaurantes/10/fornecedores': () => json([{ id: 7, nome: 'Hortifruti Verde', ativo: true }]),
}

describe('Despesas', () => {
  it('lista as despesas do mês com o total calculado pelo backend', async () => {
    const fetchFalso = simularBackend({
      ...OPCOES,
      'GET /api/restaurantes/10/despesas': () => json({ itens: [DESPESA], total: 1, valor_total: '1234.50' }),
    })

    renderizarNaArea(<Despesas />)

    const linha = (await screen.findByText('Compra de legumes')).closest('tr')!
    expect(within(linha).getByText('10/10/2026')).toBeInTheDocument()
    expect(within(linha).getByText('Alimentos e insumos')).toBeInTheDocument()
    expect(within(linha).getByText(/R\$\s1\.234,50/)).toBeInTheDocument()
    expect(screen.getByText(/1 despesa ·/)).toBeInTheDocument()

    // O filtro inicial é o mês atual.
    const consulta = chamadas(fetchFalso, 'GET', '/api/restaurantes/10/despesas')[0].url.searchParams
    expect(consulta.get('de')).toMatch(/^\d{4}-\d{2}-01$/)
    expect(consulta.get('ate')).toMatch(/^\d{4}-\d{2}-\d{2}$/)
  })

  it('filtra por categoria e volta para a primeira página', async () => {
    const fetchFalso = simularBackend({
      ...OPCOES,
      'GET /api/restaurantes/10/despesas': () => json({ itens: [], total: 0, valor_total: '0.00' }),
    })
    renderizarNaArea(<Despesas />)
    await screen.findByText('Nenhuma despesa encontrada com estes filtros.')

    await userEvent.selectOptions(screen.getByLabelText('Categoria'), 'Bebidas')

    await waitFor(() => {
      const ultima = chamadas(fetchFalso, 'GET', '/api/restaurantes/10/despesas').at(-1)!.url.searchParams
      expect(ultima.get('categoria_id')).toBe('4')
      expect(ultima.get('deslocamento')).toBe('0')
    })
  })

  it('cadastra uma despesa convertendo o valor digitado', async () => {
    const fetchFalso = simularBackend({
      ...OPCOES,
      'GET /api/restaurantes/10/despesas': () => json({ itens: [], total: 0, valor_total: '0.00' }),
      'POST /api/restaurantes/10/despesas': () => json(DESPESA, 201),
    })
    renderizarNaArea(<Despesas />)

    await userEvent.click(await screen.findByRole('button', { name: 'Nova despesa' }))
    await userEvent.type(screen.getByLabelText('Descrição'), 'Compra de legumes')
    await userEvent.type(screen.getByLabelText('Valor (R$)'), '1.234,5')
    await userEvent.clear(screen.getByLabelText('Data da despesa'))
    await userEvent.type(screen.getByLabelText('Data da despesa'), '2026-10-10')
    await userEvent.selectOptions(await screen.findByLabelText('Categoria'), 'Alimentos e insumos')
    await userEvent.selectOptions(screen.getByLabelText('Fornecedor'), 'Hortifruti Verde')
    await userEvent.click(screen.getByRole('button', { name: 'Salvar' }))

    expect(await screen.findByRole('heading', { name: 'Despesas' })).toBeInTheDocument()
    expect(corpoEnviado(chamadas(fetchFalso, 'POST', '/api/restaurantes/10/despesas')[0])).toEqual({
      descricao: 'Compra de legumes',
      valor: '1234.50',
      data: '2026-10-10',
      categoria_id: 3,
      fornecedor_id: 7,
      numero_documento: null,
      observacoes: null,
    })
  })

  it('não envia valor inválido', async () => {
    const fetchFalso = simularBackend({
      ...OPCOES,
      'GET /api/restaurantes/10/despesas': () => json({ itens: [], total: 0, valor_total: '0.00' }),
    })
    renderizarNaArea(<Despesas />)

    await userEvent.click(await screen.findByRole('button', { name: 'Nova despesa' }))
    await userEvent.type(screen.getByLabelText('Descrição'), 'Compra')
    await userEvent.type(screen.getByLabelText('Valor (R$)'), '12,345')
    await userEvent.click(screen.getByRole('button', { name: 'Salvar' }))

    expect(screen.getByRole('alert')).toHaveTextContent('Informe um valor válido')
    expect(chamadas(fetchFalso, 'POST', '/api/restaurantes/10/despesas')).toHaveLength(0)
  })

  it('exclui após confirmar', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    const fetchFalso = simularBackend({
      ...OPCOES,
      'GET /api/restaurantes/10/despesas': () => json({ itens: [DESPESA], total: 1, valor_total: '1234.50' }),
      'DELETE /api/restaurantes/10/despesas/1': semConteudo,
    })
    renderizarNaArea(<Despesas />)

    await userEvent.click(await screen.findByRole('button', { name: 'Excluir Compra de legumes' }))

    expect(chamadas(fetchFalso, 'DELETE', '/api/restaurantes/10/despesas/1')).toHaveLength(1)
    await waitFor(() => expect(chamadas(fetchFalso, 'GET', '/api/restaurantes/10/despesas')).toHaveLength(2))
  })

  it('despesa gerada por conta paga não pode ser editada aqui', async () => {
    simularBackend({
      ...OPCOES,
      'GET /api/restaurantes/10/despesas': () =>
        json({ itens: [{ ...DESPESA, conta_pagar_id: 5 }], total: 1, valor_total: '1234.50' }),
    })
    renderizarNaArea(<Despesas />)

    expect(await screen.findByText('Conta paga')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Excluir Compra de legumes' })).not.toBeInTheDocument()
  })

  it('sessão expirada volta para o login', async () => {
    simularBackend({
      ...OPCOES,
      'GET /api/restaurantes/10/despesas': () => json({ detail: 'Faça login para continuar.' }, 401),
    })

    const { sessaoExpirou } = renderizarNaArea(<Despesas />)

    await waitFor(() => expect(sessaoExpirou).toHaveBeenCalled())
  })
})
