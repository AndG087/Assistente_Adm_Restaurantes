// Único ponto do frontend que conversa com o backend.

export const TAMANHO_MAXIMO_MENSAGEM = 4000

export interface HealthResponse {
  status: 'ok'
  banco_de_dados: 'ok' | 'indisponivel'
  modo_demonstracao?: boolean
}

export interface IAStatusResponse {
  ollama_disponivel: boolean
  // null antes do login: o backend só revela qual modelo está em uso para quem está logado.
  modelo: string | null
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
  // Dados extras que o backend enviou junto com o erro (ex.: id do documento repetido).
  readonly detalhes: Record<string, unknown> | null

  constructor(mensagem: string, status: number | null, detalhes: Record<string, unknown> | null = null) {
    super(mensagem)
    this.name = 'ApiError'
    this.status = status
    this.detalhes = detalhes
  }
}

type ValorConsulta = string | number | boolean | null | undefined

/** Monta "/caminho?a=1&b=2", ignorando parâmetros vazios. */
export function comConsulta(caminho: string, parametros: Record<string, ValorConsulta>): string {
  const busca = new URLSearchParams()
  for (const [chave, valor] of Object.entries(parametros)) {
    if (valor !== null && valor !== undefined && valor !== '' && valor !== false) busca.set(chave, String(valor))
  }
  const texto = busca.toString()
  return texto ? `${caminho}?${texto}` : caminho
}

export function enviarJson(metodo: 'POST' | 'PUT', corpo: unknown): RequestInit {
  return { method: metodo, body: JSON.stringify(corpo) }
}

export async function requisitar<T>(caminho: string, init?: RequestInit): Promise<T> {
  let resposta: Response
  try {
    // Corpo em texto é JSON; em FormData (envio de arquivo), o navegador define o Content-Type sozinho.
    const ehJson = typeof init?.body === 'string'
    resposta = await fetch(caminho, {
      ...init,
      headers: { ...(ehJson ? { 'Content-Type': 'application/json' } : {}), ...init?.headers },
    })
  } catch {
    throw new ApiError('Não foi possível conectar ao Caderninho. Verifique se ele está aberto neste computador.', null)
  }

  if (!resposta.ok) {
    const [mensagem, detalhes] = await mensagemDeErro(resposta)
    throw new ApiError(mensagem, resposta.status, detalhes)
  }
  if (resposta.status === 204) {
    return undefined as T
  }
  return (await resposta.json()) as T
}

async function mensagemDeErro(resposta: Response): Promise<[string, Record<string, unknown> | null]> {
  try {
    const corpo: unknown = await resposta.json()
    if (corpo && typeof corpo === 'object' && 'detail' in corpo) {
      const { detail } = corpo
      if (typeof detail === 'string') return [detail, null]
      // Erro de validação do FastAPI: lista com uma mensagem por campo.
      if (resposta.status === 422 && Array.isArray(detail)) {
        return [mensagemDeValidacao(detail), null]
      }
      // Erro com dados extras: { mensagem: "...", ... }
      if (detail && typeof detail === 'object' && 'mensagem' in detail && typeof detail.mensagem === 'string') {
        return [detail.mensagem, detail as Record<string, unknown>]
      }
    }
  } catch {
    // Corpo sem JSON (ex.: proxy sem backend): cai na mensagem genérica abaixo.
  }
  if (resposta.status >= 500) {
    return ['O Caderninho não respondeu corretamente. Tente de novo em instantes.', null]
  }
  if (resposta.status === 422) {
    return ['Os dados enviados são inválidos. Verifique e tente novamente.', null]
  }
  return [`Erro inesperado (HTTP ${resposta.status}).`, null]
}

const NOMES_DOS_CAMPOS: Record<string, string> = {
  nome: 'Nome',
  email: 'E-mail',
  senha: 'Senha',
  cnpj: 'CNPJ',
  mensagem: 'Mensagem',
  documento: 'CPF/CNPJ',
  telefone: 'Telefone',
  observacoes: 'Observações',
  descricao: 'Descrição',
  valor: 'Valor',
  data: 'Data',
  data_vencimento: 'Vencimento',
  data_pagamento: 'Data de pagamento',
  numero_documento: 'Nº do documento',
}

const TRADUCOES: [RegExp, (m: RegExpMatchArray) => string][] = [
  [/at least (\d+) characters?/, (m) => `deve ter pelo menos ${m[1]} caracteres`],
  [/at most (\d+) characters?/, (m) => `deve ter no máximo ${m[1]} caracteres`],
  [/Field required/, () => 'é obrigatório'],
  [/valid date/, () => 'precisa ser uma data válida'],
  [/valid (decimal|number|integer)/, () => 'precisa ser um número'],
  [/no more than (\d+) decimal places?/, (m) => `deve ter no máximo ${m[1]} casas decimais`],
  [/greater than or equal to (\S+)/, (m) => `deve ser maior ou igual a ${m[1]}`],
  [/greater than (\S+)/, (m) => `deve ser maior que ${m[1]}`],
  [/less than or equal to (\S+)/, (m) => `deve ser no máximo ${m[1]}`],
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
