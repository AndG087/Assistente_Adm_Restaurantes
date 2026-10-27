import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'

type Rota = (init?: RequestInit) => Response | Promise<Response>

function json(corpo: unknown, status = 200): Response {
  return new Response(JSON.stringify(corpo), { status, headers: { 'Content-Type': 'application/json' } })
}

const ANA = { id: 1, nome: 'Ana Souza', email: 'ana@exemplo.com' }
const CANTINA = { id: 10, nome: 'Cantina da Ana', cnpj: '11222333000181', papel: 'proprietario' }

const ROTAS_PADRAO: Record<string, Rota> = {
  'GET /api/health': () => json({ status: 'ok', banco_de_dados: 'ok' }),
  'GET /api/ia/status': () => json({ ollama_disponivel: true, modelo: 'llama3.2:1b', modelo_disponivel: true }),
}

// Rotas de um usuário já logado com um restaurante.
const LOGADO: Record<string, Rota> = {
  'GET /api/auth/eu': () => json(ANA),
  'GET /api/restaurantes': () => json([CANTINA]),
}

const NAO_LOGADO: Record<string, Rota> = {
  'GET /api/auth/eu': () => json({ detail: 'Faça login para continuar.' }, 401),
}

function simularBackend(rotas: Record<string, Rota>) {
  const todas = { ...ROTAS_PADRAO, ...rotas }
  const fetchFalso = vi.fn(async (entrada: RequestInfo | URL, init?: RequestInit) => {
    const rota = todas[`${init?.method ?? 'GET'} ${String(entrada)}`]
    if (!rota) throw new TypeError('Failed to fetch')
    return rota(init)
  })
  vi.stubGlobal('fetch', fetchFalso)
  return fetchFalso
}

function chamadas(fetchFalso: ReturnType<typeof simularBackend>, metodo: string, url: string) {
  return fetchFalso.mock.calls.filter(([u, init]) => u === url && (init?.method ?? 'GET') === metodo)
}

async function enviarNoChat(texto: string) {
  await userEvent.type(await screen.findByLabelText('Mensagem para a IA'), texto)
  await userEvent.click(screen.getByRole('button', { name: 'Enviar' }))
}

beforeEach(() => {
  try {
    localStorage.clear()
  } catch {
    // ambiente sem localStorage
  }
})

describe('Acesso', () => {
  it('mostra a tela de login e o status quando não há sessão', async () => {
    simularBackend(NAO_LOGADO)

    render(<App />)

    expect(await screen.findByRole('heading', { name: 'Acesse sua conta' })).toBeInTheDocument()
    expect(screen.getByText('Conectado')).toBeInTheDocument()
    expect(screen.getByText('llama3.2:1b')).toBeInTheDocument()
    expect(screen.queryByLabelText('Mensagem para a IA')).not.toBeInTheDocument()
  })

  it('indica backend fora do ar e permite tentar de novo', async () => {
    simularBackend({ 'GET /api/health': () => Promise.reject(new TypeError('Failed to fetch')) })

    render(<App />)

    expect(await screen.findByText('Desconectado')).toBeInTheDocument()
    expect(await screen.findByRole('alert')).toHaveTextContent('Não foi possível conectar ao backend')
    expect(screen.getByRole('button', { name: 'Tentar novamente' })).toBeInTheDocument()
  })

  it('faz login e, sem restaurantes, pede o cadastro do primeiro', async () => {
    const fetchFalso = simularBackend({
      ...NAO_LOGADO,
      'POST /api/auth/login': () => json(ANA),
      'GET /api/restaurantes': () => json([]),
    })
    render(<App />)

    await userEvent.type(await screen.findByLabelText('E-mail'), 'ana@exemplo.com')
    await userEvent.type(screen.getByLabelText('Senha'), 'senha-segura-123')
    await userEvent.click(screen.getByRole('button', { name: 'Entrar' }))

    expect(await screen.findByRole('heading', { name: 'Cadastre seu restaurante' })).toBeInTheDocument()
    expect(screen.getByText('Ana Souza')).toBeInTheDocument()
    const [, init] = chamadas(fetchFalso, 'POST', '/api/auth/login')[0]
    expect(JSON.parse(String(init?.body))).toEqual({ email: 'ana@exemplo.com', senha: 'senha-segura-123' })
  })

  it('mostra o erro de login sem sair da tela', async () => {
    simularBackend({
      ...NAO_LOGADO,
      'POST /api/auth/login': () => json({ detail: 'E-mail ou senha inválidos.' }, 401),
    })
    render(<App />)

    await userEvent.type(await screen.findByLabelText('E-mail'), 'ana@exemplo.com')
    await userEvent.type(screen.getByLabelText('Senha'), 'errada')
    await userEvent.click(screen.getByRole('button', { name: 'Entrar' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('E-mail ou senha inválidos.')
    expect(screen.getByRole('heading', { name: 'Acesse sua conta' })).toBeInTheDocument()
  })

  it('traduz erros de validação do backend', async () => {
    simularBackend({
      ...NAO_LOGADO,
      'POST /api/auth/registrar': () =>
        json(
          { detail: [{ loc: ['body', 'email'], msg: 'Value error, E-mail inválido.', type: 'value_error' }] },
          422,
        ),
    })
    render(<App />)

    await userEvent.click(await screen.findByRole('tab', { name: 'Criar conta' }))
    await userEvent.type(screen.getByLabelText('Nome'), 'Ana')
    await userEvent.type(screen.getByLabelText('E-mail'), 'ana@exemplo.com')
    await userEvent.type(screen.getByLabelText('Senha'), 'senha-segura-123')
    await userEvent.click(screen.getByRole('button', { name: 'Criar conta' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('E-mail inválido.')
  })

  it('cria a conta, cadastra o restaurante e chega ao chat', async () => {
    const fetchFalso = simularBackend({
      ...NAO_LOGADO,
      'POST /api/auth/registrar': () => json(ANA, 201),
      'GET /api/restaurantes': () => json([]),
      'POST /api/restaurantes': () => json(CANTINA, 201),
    })
    render(<App />)

    await userEvent.click(await screen.findByRole('tab', { name: 'Criar conta' }))
    await userEvent.type(screen.getByLabelText('Nome'), 'Ana Souza')
    await userEvent.type(screen.getByLabelText('E-mail'), 'ana@exemplo.com')
    await userEvent.type(screen.getByLabelText('Senha'), 'senha-segura-123')
    await userEvent.click(screen.getByRole('button', { name: 'Criar conta' }))

    await userEvent.type(await screen.findByLabelText('Nome do restaurante'), 'Cantina da Ana')
    await userEvent.type(screen.getByLabelText('CNPJ (opcional)'), '11.222.333/0001-81')
    await userEvent.click(screen.getByRole('button', { name: 'Cadastrar restaurante' }))

    const painel = await screen.findByRole('region', { name: 'Restaurante selecionado' })
    expect(within(painel).getByRole('combobox')).toHaveDisplayValue('Cantina da Ana')
    expect(within(painel).getByText('11.222.333/0001-81')).toBeInTheDocument()
    expect(within(painel).getByText('Proprietário')).toBeInTheDocument()
    expect(screen.getByLabelText('Mensagem para a IA')).toBeInTheDocument()

    const [, init] = chamadas(fetchFalso, 'POST', '/api/restaurantes')[0]
    expect(JSON.parse(String(init?.body))).toEqual({ nome: 'Cantina da Ana', cnpj: '11.222.333/0001-81' })
  })

  it('sai da conta e volta para o login', async () => {
    const fetchFalso = simularBackend({ ...LOGADO, 'POST /api/auth/logout': () => new Response(null, { status: 204 }) })
    render(<App />)

    await userEvent.click(await screen.findByRole('button', { name: 'Sair' }))

    expect(await screen.findByRole('heading', { name: 'Acesse sua conta' })).toBeInTheDocument()
    expect(chamadas(fetchFalso, 'POST', '/api/auth/logout')).toHaveLength(1)
  })
})

describe('Restaurantes', () => {
  it('troca o restaurante selecionado', async () => {
    simularBackend({
      ...LOGADO,
      'GET /api/restaurantes': () =>
        json([{ id: 20, nome: 'Ana Lanches', cnpj: null, papel: 'proprietario' }, CANTINA]),
    })
    render(<App />)

    const seletor = await screen.findByRole('combobox')
    expect(seletor).toHaveDisplayValue('Ana Lanches')
    expect(screen.getByText('Não informado')).toBeInTheDocument()

    await userEvent.selectOptions(seletor, 'Cantina da Ana')

    expect(seletor).toHaveDisplayValue('Cantina da Ana')
    expect(screen.getByText('11.222.333/0001-81')).toBeInTheDocument()
  })
})

describe('Chat', () => {
  it('avisa quando o modelo não está instalado', async () => {
    simularBackend({
      ...LOGADO,
      'GET /api/ia/status': () => json({ ollama_disponivel: true, modelo: 'llama3.2:1b', modelo_disponivel: false }),
    })

    render(<App />)

    expect(await screen.findByText(/ollama pull llama3.2:1b/)).toBeInTheDocument()
  })

  it('envia a mensagem, mostra o carregamento e exibe a resposta da IA', async () => {
    let responder: (r: Response) => void = () => {}
    const fetchFalso = simularBackend({
      ...LOGADO,
      'POST /api/ia/chat': () => new Promise((resolve) => (responder = resolve)),
    })
    render(<App />)

    await enviarNoChat('Olá')

    expect(screen.getByText('Olá')).toBeInTheDocument()
    expect(screen.getByLabelText('A IA está gerando a resposta')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Enviar' })).toBeDisabled()

    responder(json({ resposta: 'Olá! Como posso ajudar?', modelo: 'llama3.2:1b' }))

    expect(await screen.findByText('Olá! Como posso ajudar?')).toBeInTheDocument()
    expect(screen.queryByLabelText('A IA está gerando a resposta')).not.toBeInTheDocument()
    const [, init] = chamadas(fetchFalso, 'POST', '/api/ia/chat')[0]
    expect(JSON.parse(String(init?.body))).toEqual({ mensagem: 'Olá' })
  })

  it('mostra o erro do backend quando a IA está indisponível, sem inventar resposta', async () => {
    simularBackend({
      ...LOGADO,
      'POST /api/ia/chat': () => json({ detail: 'O serviço de IA local (Ollama) não está acessível.' }, 503),
    })
    render(<App />)

    await enviarNoChat('Olá')

    expect(await screen.findByRole('alert')).toHaveTextContent('O serviço de IA local (Ollama) não está acessível.')
    expect(document.querySelector('.mensagem--ia')).toBeNull()
  })

  it('verifica o status novamente depois de uma falha no chat', async () => {
    const fetchFalso = simularBackend({
      ...LOGADO,
      'POST /api/ia/chat': () => json({ detail: 'A IA demorou demais para responder. Tente novamente.' }, 504),
    })
    render(<App />)

    await enviarNoChat('Olá')

    await screen.findByRole('alert')
    await waitFor(() => expect(chamadas(fetchFalso, 'GET', '/api/ia/status')).toHaveLength(2))
  })

  it('volta para o login quando a sessão expira', async () => {
    simularBackend({
      ...LOGADO,
      'POST /api/ia/chat': () => json({ detail: 'Faça login para continuar.' }, 401),
    })
    render(<App />)

    await enviarNoChat('Olá')

    expect(await screen.findByRole('heading', { name: 'Acesse sua conta' })).toBeInTheDocument()
  })
})
