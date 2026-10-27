import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { ChatInput } from './ChatInput'

describe('ChatInput', () => {
  it('desabilita o envio quando o campo está vazio ou só com espaços', async () => {
    render(<ChatInput onEnviar={vi.fn()} desabilitado={false} />)
    const botao = screen.getByRole('button', { name: 'Enviar' })

    expect(botao).toBeDisabled()
    await userEvent.type(screen.getByLabelText('Mensagem para a IA'), '   ')
    expect(botao).toBeDisabled()
  })

  it('envia a mensagem sem espaços nas pontas e limpa o campo', async () => {
    const onEnviar = vi.fn()
    render(<ChatInput onEnviar={onEnviar} desabilitado={false} />)
    const campo = screen.getByLabelText('Mensagem para a IA')

    await userEvent.type(campo, '  Olá  ')
    await userEvent.click(screen.getByRole('button', { name: 'Enviar' }))

    expect(onEnviar).toHaveBeenCalledExactlyOnceWith('Olá')
    expect(campo).toHaveValue('')
  })

  it('envia com Enter e quebra linha com Shift+Enter', async () => {
    const onEnviar = vi.fn()
    render(<ChatInput onEnviar={onEnviar} desabilitado={false} />)
    const campo = screen.getByLabelText('Mensagem para a IA')

    await userEvent.type(campo, 'linha 1{Shift>}{Enter}{/Shift}linha 2')
    expect(onEnviar).not.toHaveBeenCalled()
    expect(campo).toHaveValue('linha 1\nlinha 2')

    await userEvent.type(campo, '{Enter}')
    expect(onEnviar).toHaveBeenCalledExactlyOnceWith('linha 1\nlinha 2')
  })

  it('não envia enquanto está desabilitado', async () => {
    const onEnviar = vi.fn()
    render(<ChatInput onEnviar={onEnviar} desabilitado />)

    await userEvent.type(screen.getByLabelText('Mensagem para a IA'), 'Olá{Enter}')

    expect(onEnviar).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: 'Enviar' })).toBeDisabled()
  })
})
