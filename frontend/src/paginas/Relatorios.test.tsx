import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { GraficoMensal } from '../components/GraficoMensal'
import { json, renderizarNaArea, simularBackend } from '../test/backendFalso'
import { Relatorios } from './Relatorios'

function mes(rotulo: string, valor: string, quantidade = 1) {
  const [nome, ano] = rotulo.split('/')
  const numero = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'].indexOf(nome) + 1
  return { ano: Number(ano), mes: numero, rotulo, quantidade, valor_total: valor }
}

const MESES = [mes('ago/2026', '1500.00', 3), mes('set/2026', '0.00', 0), mes('out/2026', '320.50', 2)]

const ROTAS = {
  'GET /api/restaurantes/10/relatorios/mensal': () => json({ meses: MESES, media_mensal: '750.00' }),
  'GET /api/restaurantes/10/despesas/resumo': () =>
    json({
      quantidade: 3,
      valor_total: '2920.00',
      por_categoria: [
        { categoria: { id: 1, nome: 'Aluguel' }, quantidade: 1, valor_total: '2500.00' },
        { categoria: null, quantidade: 2, valor_total: '420.00' },
      ],
    }),
  'GET /api/restaurantes/10/relatorios/fornecedores': () =>
    json([{ fornecedor: { id: 7, nome: 'Distribuidora Sul' }, quantidade: 1, valor_total: '300.00' }]),
}

describe('Relatórios', () => {
  it('mostra totais, gráfico mensal e barras com valores escritos', async () => {
    simularBackend(ROTAS)

    renderizarNaArea(<Relatorios />)

    const totais = await screen.findByLabelText('Totais do período')
    expect(within(totais).getByText(/R\$\s2\.920,00/)).toBeInTheDocument()
    expect(within(totais).getByText(/R\$\s750,00/)).toBeInTheDocument()
    expect(screen.getByRole('listitem', { name: /ago\/2026: R\$\s1\.500,00 em 3 lançamentos/ })).toBeInTheDocument()
    const categorias = screen.getByRole('list', { name: 'Despesas por categoria' })
    expect(within(categorias).getByText('Sem categoria')).toBeInTheDocument()
    expect(within(categorias).getByText(/2 lançamentos/)).toBeInTheDocument()
    expect(await screen.findByText('Distribuidora Sul')).toBeInTheDocument()
  })

  it('links de exportação levam o período escolhido', async () => {
    simularBackend(ROTAS)
    renderizarNaArea(<Relatorios />)

    const de = screen.getByLabelText('De')
    await userEvent.clear(de)
    await userEvent.type(de, '2026-09-01')

    const link = screen.getByRole('link', { name: 'Exportar despesas (CSV)' })
    const url = new URL(link.getAttribute('href')!, 'http://teste.local')
    expect(url.pathname).toBe('/api/restaurantes/10/relatorios/despesas.csv')
    expect(url.searchParams.get('de')).toBe('2026-09-01')
    expect(link).toHaveAttribute('download')
  })

  it('período invertido desativa a exportação e avisa', async () => {
    simularBackend(ROTAS)
    renderizarNaArea(<Relatorios />)

    const de = screen.getByLabelText('De')
    await userEvent.clear(de)
    await userEvent.type(de, '2099-01-01')

    expect(screen.getByRole('alert')).toHaveTextContent('Escolha um período válido')
    expect(screen.queryByRole('link', { name: 'Exportar despesas (CSV)' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Exportar (CSV)' })).toBeDisabled()
  })
})

describe('Gráfico mensal', () => {
  it('rotula só o maior mês e o atual, e toda coluna é focável', () => {
    renderizarNaArea(<GraficoMensal meses={MESES} />)

    const colunas = screen.getAllByRole('listitem')
    expect(colunas).toHaveLength(3)
    colunas.forEach((c) => expect(c).toHaveAttribute('tabindex', '0'))
    // Rótulos escritos: maior (ago) e atual (out); setembro (zero) não.
    expect(document.querySelectorAll('.coluna__valor')).toHaveLength(2)
  })

  it('a tabela traz todos os valores sem depender do mouse', () => {
    renderizarNaArea(<GraficoMensal meses={MESES} />)

    const tabela = screen.getByRole('table')
    expect(within(tabela).getAllByRole('row')).toHaveLength(4)
    expect(within(tabela).getByText(/R\$\s0,00/)).toBeInTheDocument()
  })

  it('sem nenhum gasto, as colunas ficam em zero sem quebrar a escala', () => {
    renderizarNaArea(<GraficoMensal meses={[mes('set/2026', '0.00', 0), mes('out/2026', '0.00', 0)]} />)

    expect(document.querySelectorAll('.coluna__valor')).toHaveLength(0)
    document.querySelectorAll<HTMLElement>('.coluna__barra').forEach((b) => expect(b.style.height).toBe('0%'))
  })
})
