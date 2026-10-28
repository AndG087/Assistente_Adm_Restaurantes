import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { chamadas, corpoEnviado, json, renderizarNaArea, simularBackend } from '../test/backendFalso'
import { ChatWindow } from './ChatWindow'

const STATUS_OK = { ollama_disponivel: true, modelo: 'llama3.2:1b', modelo_disponivel: true }

function renderizar(statusIA = STATUS_OK) {
  return renderizarNaArea(<ChatWindow statusIA={statusIA} onFalha={() => {}} onSessaoExpirada={() => {}} />)
}

describe('Assistente', () => {
  it('pergunta de exemplo traz a resposta com a origem e a tabela', async () => {
    const fetchFalso = simularBackend({
      'POST /api/restaurantes/10/assistente': () =>
        json({
          resposta: 'Há 1 conta vencida, somando R$ 800,40:',
          origem: 'dados',
          consulta: 'Contas vencidas · até 19/10/2026',
          interpretado_por: 'regras',
          tabela: { colunas: ['Vencimento', 'Descrição', 'Valor'], linhas: [['15/10/2026', 'Energia', 'R$ 800,40']] },
        }),
    })
    renderizar()

    await userEvent.click(screen.getByRole('button', { name: 'Tenho contas vencidas?' }))

    const resposta = (await screen.findByText('Há 1 conta vencida, somando R$ 800,40:')).closest('.mensagem')!
    expect(within(resposta as HTMLElement).getByText('Dados do restaurante · Contas vencidas · até 19/10/2026')).toBeInTheDocument()
    expect(within(resposta as HTMLElement).getByRole('cell', { name: 'Energia' })).toBeInTheDocument()
    expect(corpoEnviado(chamadas(fetchFalso, 'POST', '/api/restaurantes/10/assistente')[0])).toEqual({
      mensagem: 'Tenho contas vencidas?',
    })
  })

  it('identifica a conversa geral sem acesso aos dados', async () => {
    simularBackend({
      'POST /api/restaurantes/10/assistente': () =>
        json({ resposta: 'Olá!', origem: 'conversa', consulta: null, interpretado_por: null, tabela: null }),
    })
    renderizar()

    await userEvent.type(screen.getByLabelText('Mensagem para a IA'), 'Oi{Enter}')

    expect(await screen.findByText('Conversa geral · sem acesso aos dados do restaurante')).toBeInTheDocument()
  })

  it('avisa que os dados funcionam mesmo com o Ollama desligado', () => {
    simularBackend({})
    renderizar({ ollama_disponivel: false, modelo: 'llama3.2:1b', modelo_disponivel: false })

    expect(screen.getByText(/Perguntas sobre os dados \(gastos, contas\) continuam funcionando/)).toBeInTheDocument()
  })
})
