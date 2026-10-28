import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it } from 'vitest'
import App from './App'
import { chamadas as chamadasA, json, simularBackend as simular, type Rota } from './test/backendFalso'

const ANA = { id: 1, nome: 'Ana Souza', email: 'ana@exemplo.com' }
const CANTINA = { id: 10, nome: 'Cantina da Ana', cnpj: '11222333000181', papel: 'proprietario' }

const ROTAS_PADRAO: Record<string, Rota> = {
  'GET /api/health': () => json({ status: 'ok', banco_de_dados: 'ok' }),
  'GET /api/ia/status': () => json({ ollama_disponivel: true, modelo: 'llama3.2:1b', modelo_disponivel: true }),
  'GET /api/restaurantes/*/contas-a-pagar/alertas': () =>
    json({
      hoje: '2026-10-20',
      dias: 7,
      vencidas: { quantidade: 0, valor_total: '0.00' },
      vencem_hoje: { quantidade: 0, valor_total: '0.00' },
      proximos_dias: { quantidade: 0, valor_total: '0.00' },
    }),
  'GET /api/restaurantes/*/despesas/resumo': () => json({ quantidade: 0, valor_total: '0.00', por_categoria: [] }),
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
  return simular({ ...ROTAS_PADRAO, ...rotas })
}

function chamadas(fetchFalso: ReturnType<typeof simularBackend>, metodo: string, url: string) {
  return chamadasA(fetchFalso, metodo, url).map((c) => [c.url.pathname, c.init] as const)
}

async function abrirAssistente() {
  await userEvent.click(await screen.findByRole('link', { name: 'Assistente' }))
}

async function enviarNoChat(texto: string) {
  await abrirAssistente()
  await userEvent.type(await screen.findByLabelText('Mensagem para a IA'), texto)
  await userEvent.click(screen.getByRole('button', { name: 'Enviar' }))
}

beforeEach(() => {
  window.location.hash = ''
  try {
    localStorage.clear()
  } catch {
    // ambiente sem localStorage
  }
  delete document.documentElement.dataset.tema
})

describe('Tema', () => {
  it('abre no claro e troca para o escuro, lembrando a escolha', async () => {
    simularBackend(NAO_LOGADO)
    render(<App />)

    expect(document.documentElement.dataset.tema).toBeUndefined()
    await userEvent.click(await screen.findByRole('button', { name: 'Tema escuro' }))

    expect(document.documentElement.dataset.tema).toBe('escuro')
    expect(localStorage.getItem('caderninho-tema')).toBe('escuro')

    await userEvent.click(screen.getByRole('button', { name: 'Tema claro' }))
    expect(document.documentElement.dataset.tema).toBeUndefined()
    expect(localStorage.getItem('caderninho-tema')).toBe('claro')
  })

  it('reabre no tema escolhido da última vez', async () => {
    localStorage.setItem('caderninho-tema', 'escuro')
    simularBackend(NAO_LOGADO)
    render(<App />)

    expect(await screen.findByRole('button', { name: 'Tema claro' })).toBeInTheDocument()
    expect(document.documentElement.dataset.tema).toBe('escuro')
  })

  it('também está na barra lateral', async () => {
    simularBackend(LOGADO)
    render(<App />)

    const menu = await screen.findByRole('complementary', { name: 'Menu' })
    expect(within(menu).getByRole('button', { name: 'Tema escuro' })).toBeInTheDocument()
  })
})

describe('Acesso', () => {
  it('mostra a tela de login e o status quando não há sessão', async () => {
    simularBackend(NAO_LOGADO)

    render(<App />)

    expect(await screen.findByRole('heading', { name: 'Acesse sua conta' })).toBeInTheDocument()
    // A apresentação do produto vem ao lado do formulário.
    expect(screen.getByRole('heading', { name: /O caderninho de contas do seu restaurante/ })).toBeInTheDocument()
    // Com tudo funcionando, o topo fica limpo: nada de "backend" ou nome de modelo à vista.
    expect(await screen.findByText('Tudo funcionando')).toBeInTheDocument()
    expect(screen.queryByText(/backend/i)).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Mensagem para a IA')).not.toBeInTheDocument()
  })

  it('mostra a faixa de demonstração só no modo de demonstração', async () => {
    simularBackend({ ...NAO_LOGADO, 'GET /api/health': () => json({ status: 'ok', banco_de_dados: 'ok', modo_demonstracao: true }) })

    render(<App />)

    expect(await screen.findByRole('note')).toHaveTextContent('todos os dados são fictícios')
  })

  it('sem modo de demonstração, não há faixa', async () => {
    simularBackend(NAO_LOGADO)

    render(<App />)

    await screen.findByRole('heading', { name: 'Acesse sua conta' })
    expect(screen.queryByRole('note')).not.toBeInTheDocument()
  })

  it('indica backend fora do ar e permite tentar de novo', async () => {
    simularBackend({ 'GET /api/health': () => Promise.reject(new TypeError('Failed to fetch')) })

    render(<App />)

    expect(await screen.findByText('Sistema desconectado')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Verificar novamente' })).toBeInTheDocument()
    expect(await screen.findByRole('alert')).toHaveTextContent('Não foi possível conectar ao Caderninho')
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
    // Depois do cadastro, a área logada abre na página inicial.
    expect(await screen.findByRole('heading', { name: 'Vencimentos' })).toBeInTheDocument()

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

describe('Barra lateral', () => {
  it('agrupa as telas e marca a atual', async () => {
    simularBackend(LOGADO)
    render(<App />)

    const menu = await screen.findByRole('navigation', { name: 'Seções' })
    expect(within(menu).getByText('Dia a dia')).toBeInTheDocument()
    expect(within(menu).getByText('Cadastros')).toBeInTheDocument()
    expect(within(menu).getByRole('link', { name: 'Início' })).toHaveAttribute('aria-current', 'page')
    expect(screen.getByRole('link', { name: 'Enviar nota ou boleto' })).toHaveAttribute('href', '#/documentos')

    await userEvent.click(within(menu).getByRole('link', { name: 'Contas a pagar' }))

    await waitFor(() =>
      expect(within(menu).getByRole('link', { name: 'Contas a pagar' })).toHaveAttribute('aria-current', 'page'),
    )
  })

  it('no celular, o menu abre pelo botão e fecha com Esc ou ao escolher uma tela', async () => {
    simularBackend(LOGADO)
    render(<App />)

    const abrir = await screen.findByRole('button', { name: 'Abrir menu' })
    const menu = screen.getByRole('complementary', { name: 'Menu' })
    expect(abrir).toHaveAttribute('aria-expanded', 'false')

    await userEvent.click(abrir)
    expect(abrir).toHaveAttribute('aria-expanded', 'true')
    expect(menu).toHaveClass('menu-lateral--aberto')

    await userEvent.keyboard('{Escape}')
    expect(abrir).toHaveAttribute('aria-expanded', 'false')

    await userEvent.click(abrir)
    await userEvent.click(within(menu).getByRole('link', { name: 'Despesas' }))
    expect(abrir).toHaveAttribute('aria-expanded', 'false')
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
    // Sem CNPJ cadastrado, a barra lateral não mostra nada (em vez de "Não informado").
    expect(screen.queryByText('11.222.333/0001-81')).not.toBeInTheDocument()

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
    await abrirAssistente()

    expect(await screen.findByText(/ollama pull llama3.2:1b/)).toBeInTheDocument()
  })

  it('envia a mensagem, mostra o carregamento e exibe a resposta da IA', async () => {
    let responder: (r: Response) => void = () => {}
    const fetchFalso = simularBackend({
      ...LOGADO,
      'POST /api/restaurantes/*/assistente': () => new Promise((resolve) => (responder = resolve)),
    })
    render(<App />)

    await enviarNoChat('Olá')

    expect(screen.getByText('Olá')).toBeInTheDocument()
    expect(screen.getByLabelText('O assistente está preparando a resposta')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Enviar' })).toBeDisabled()

    responder(
      json({ resposta: 'Olá! Como posso ajudar?', origem: 'conversa', consulta: null, interpretado_por: null, tabela: null }),
    )

    expect(await screen.findByText('Olá! Como posso ajudar?')).toBeInTheDocument()
    expect(screen.queryByLabelText('O assistente está preparando a resposta')).not.toBeInTheDocument()
    const [, init] = chamadas(fetchFalso, 'POST', '/api/restaurantes/10/assistente')[0]
    expect(JSON.parse(String(init?.body))).toEqual({ mensagem: 'Olá' })
  })

  it('mostra o erro do backend quando a IA está indisponível, sem inventar resposta', async () => {
    simularBackend({
      ...LOGADO,
      'POST /api/restaurantes/*/assistente': () => json({ detail: 'O serviço de IA local (Ollama) não está acessível.' }, 503),
    })
    render(<App />)

    await enviarNoChat('Olá')

    expect(await screen.findByRole('alert')).toHaveTextContent('O serviço de IA local (Ollama) não está acessível.')
    expect(document.querySelector('.mensagem--ia')).toBeNull()
  })

  it('verifica o status novamente depois de uma falha no chat', async () => {
    const fetchFalso = simularBackend({
      ...LOGADO,
      'POST /api/restaurantes/*/assistente': () => json({ detail: 'A IA demorou demais para responder. Tente novamente.' }, 504),
    })
    render(<App />)
    const consultasDoStatus = () => chamadas(fetchFalso, 'GET', '/api/ia/status').length

    // Ao abrir e de novo ao confirmar o login (o nome do modelo só vem para quem está logado).
    await waitFor(() => expect(consultasDoStatus()).toBe(2))
    await enviarNoChat('Olá')

    await screen.findByRole('alert')
    await waitFor(() => expect(consultasDoStatus()).toBe(3))
  })

  it('antes do login o cabeçalho não mostra qual modelo de IA está em uso', async () => {
    simularBackend({
      ...NAO_LOGADO,
      'GET /api/ia/status': () => json({ ollama_disponivel: true, modelo: null, modelo_disponivel: true }),
    })
    render(<App />)

    expect(await screen.findByText('Tudo funcionando')).toBeInTheDocument()
    expect(screen.queryByText(/llama3\.2/)).not.toBeInTheDocument()
  })

  it('volta para o login quando a sessão expira', async () => {
    simularBackend({
      ...LOGADO,
      'POST /api/restaurantes/*/assistente': () => json({ detail: 'Faça login para continuar.' }, 401),
    })
    render(<App />)

    await enviarNoChat('Olá')

    expect(await screen.findByRole('heading', { name: 'Acesse sua conta' })).toBeInTheDocument()
  })
})
