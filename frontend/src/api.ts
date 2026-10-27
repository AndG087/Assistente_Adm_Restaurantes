// Único ponto do frontend que conversa com o backend.

export const TAMANHO_MAXIMO_MENSAGEM = 4000

export interface HealthResponse {
  status: 'ok'
  banco_de_dados: 'ok' | 'indisponivel'
}

export interface IAStatusResponse {
  ollama_disponivel: boolean
  modelo: string
  modelo_disponivel: boolean
}

export interface ChatResponse {
  resposta: string
  modelo: string
}

export interface Usuario {
  id: number
  nome: string
  email: string
}

export interface Restaurante {
  id: number
  nome: string
  cnpj: string | null
  papel: 'proprietario' | 'membro'
}

export class ApiError extends Error {
  readonly status: number | null

  constructor(mensagem: string, status: number | null) {
    super(mensagem)
    this.name = 'ApiError'
    this.status = status
  }
}

async function requisitar<T>(caminho: string, init?: RequestInit): Promise<T> {
  let resposta: Response
  try {
    resposta = await fetch(caminho, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...init?.headers },
    })
  } catch {
    throw new ApiError('Não foi possível conectar ao backend. Verifique se ele está em execução.', null)
  }

  if (!resposta.ok) {
    throw new ApiError(await mensagemDeErro(resposta), resposta.status)
  }
  if (resposta.status === 204) {
    return undefined as T
  }
  return (await resposta.json()) as T
}

async function mensagemDeErro(resposta: Response): Promise<string> {
  try {
    const corpo: unknown = await resposta.json()
    if (corpo && typeof corpo === 'object' && 'detail' in corpo) {
      if (typeof corpo.detail === 'string') return corpo.detail
      // Erro de validação do FastAPI: lista com uma mensagem por campo.
      if (resposta.status === 422 && Array.isArray(corpo.detail)) {
        return mensagemDeValidacao(corpo.detail)
      }
    }
  } catch {
    // Corpo sem JSON (ex.: proxy sem backend): cai na mensagem genérica abaixo.
  }
  if (resposta.status >= 500) {
    return 'O backend não respondeu corretamente. Verifique se ele está em execução.'
  }
  if (resposta.status === 422) {
    return 'Os dados enviados são inválidos. Verifique e tente novamente.'
  }
  return `Erro inesperado (HTTP ${resposta.status}).`
}

const NOMES_DOS_CAMPOS: Record<string, string> = {
  nome: 'Nome',
  email: 'E-mail',
  senha: 'Senha',
  cnpj: 'CNPJ',
  mensagem: 'Mensagem',
}

const TRADUCOES: [RegExp, (m: RegExpMatchArray) => string][] = [
  [/at least (\d+) characters?/, (m) => `deve ter pelo menos ${m[1]} caracteres`],
  [/at most (\d+) characters?/, (m) => `deve ter no máximo ${m[1]} caracteres`],
  [/Field required/, () => 'é obrigatório'],
  [/^Value error, (.*)$/, (m) => m[1]],
]

function mensagemDeValidacao(erros: unknown[]): string {
  const primeiro = erros[0] as { loc?: unknown[]; msg?: string } | undefined
  if (!primeiro?.msg) return 'Os dados enviados são inválidos.'
  const campo = String(primeiro.loc?.at(-1) ?? '')
  for (const [padrao, traduzir] of TRADUCOES) {
    const encontrado = primeiro.msg.match(padrao)
    if (encontrado) {
      const texto = traduzir(encontrado)
      // Mensagens do próprio backend ("E-mail inválido.") já são frases completas.
      if (padrao.source.startsWith('^Value error')) return texto
      return `${NOMES_DOS_CAMPOS[campo] ?? 'Campo'} ${texto}.`
    }
  }
  return 'Os dados enviados são inválidos. Verifique e tente novamente.'
}

export function buscarSaude(): Promise<HealthResponse> {
  return requisitar('/api/health')
}

export function buscarStatusIA(): Promise<IAStatusResponse> {
  return requisitar('/api/ia/status')
}

export function enviarMensagem(mensagem: string): Promise<ChatResponse> {
  return requisitar('/api/ia/chat', { method: 'POST', body: JSON.stringify({ mensagem }) })
}

// --- Autenticação (a sessão fica num cookie HttpOnly que o navegador envia sozinho) ---

export function buscarUsuarioAtual(): Promise<Usuario> {
  return requisitar('/api/auth/eu')
}

export function entrar(email: string, senha: string): Promise<Usuario> {
  return requisitar('/api/auth/login', { method: 'POST', body: JSON.stringify({ email, senha }) })
}

export function cadastrar(nome: string, email: string, senha: string): Promise<Usuario> {
  return requisitar('/api/auth/registrar', { method: 'POST', body: JSON.stringify({ nome, email, senha }) })
}

export function sair(): Promise<void> {
  return requisitar('/api/auth/logout', { method: 'POST' })
}

// --- Restaurantes ---

export function listarRestaurantes(): Promise<Restaurante[]> {
  return requisitar('/api/restaurantes')
}

export function criarRestaurante(nome: string, cnpj: string): Promise<Restaurante> {
  return requisitar('/api/restaurantes', { method: 'POST', body: JSON.stringify({ nome, cnpj: cnpj || null }) })
}
