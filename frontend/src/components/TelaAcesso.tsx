import { useState, type FormEvent } from 'react'
import type { Sessao } from '../hooks/useSessao'
import { Logo } from './Logo'

// Só o que o sistema já faz hoje: a vitrine não promete nada que a demonstração não mostre.
const BENEFICIOS = [
  [
    'Lê notas e boletos',
    'Envie o PDF ou a foto da nota: valor, data e fornecedor já chegam preenchidos para você conferir.',
  ],
  ['Avisa o que vence', 'Contas vencidas, de hoje e da semana logo na primeira tela. Pagou? A despesa entra sozinha.'],
  ['Responde suas perguntas', '"Quanto gastei com bebidas este mês?" A resposta vem dos números do seu restaurante.'],
] as const

function Vitrine() {
  return (
    <section className="vitrine" aria-labelledby="titulo-vitrine">
      <Logo tamanho={56} />
      <h2 id="titulo-vitrine" className="vitrine__titulo">
        O caderninho de contas do seu restaurante, agora sem papelada.
      </h2>
      <p className="vitrine__texto">
        Notas, boletos e contas a pagar num lugar só, com uma IA que lê os documentos para você.
      </p>
      <ul className="vitrine__beneficios">
        {BENEFICIOS.map(([titulo, texto]) => (
          <li key={titulo}>
            <span className="vitrine__marca" aria-hidden="true">
              ✓
            </span>
            <span>
              <strong>{titulo}</strong>
              {texto}
            </span>
          </li>
        ))}
      </ul>
      <p className="vitrine__privacidade">Seus dados ficam no seu computador. Nada é enviado para a internet.</p>
    </section>
  )
}

type Modo = 'entrar' | 'cadastrar'

interface TelaAcessoProps {
  sessao: Sessao
}

export function TelaAcesso({ sessao }: TelaAcessoProps) {
  const [modo, setModo] = useState<Modo>('entrar')
  const [nome, setNome] = useState('')
  const [email, setEmail] = useState('')
  const [senha, setSenha] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [erro, setErro] = useState<string | null>(null)

  function trocarModo(novo: Modo) {
    setModo(novo)
    setErro(null)
  }

  async function aoSubmeter(evento: FormEvent) {
    evento.preventDefault()
    setEnviando(true)
    setErro(null)
    try {
      if (modo === 'entrar') {
        await sessao.entrar(email, senha)
      } else {
        await sessao.cadastrar(nome, email, senha)
      }
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'Erro inesperado.')
      setEnviando(false)
    }
  }

  const cadastro = modo === 'cadastrar'

  return (
    <div className="acesso-vitrine">
      <Vitrine />
      <section className="cartao acesso" aria-labelledby="titulo-acesso">
        <div className="abas" role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={!cadastro}
            className="abas__item"
            onClick={() => trocarModo('entrar')}
          >
            Entrar
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={cadastro}
            className="abas__item"
            onClick={() => trocarModo('cadastrar')}
          >
            Criar conta
          </button>
        </div>

        <form className="formulario" onSubmit={aoSubmeter}>
          <h2 id="titulo-acesso" className="formulario__titulo">
            {cadastro ? 'Crie sua conta' : 'Acesse sua conta'}
          </h2>

          {sessao.erroVerificacao && (
            <p className="alerta alerta--erro" role="alert">
              {sessao.erroVerificacao}{' '}
              <button type="button" className="link" onClick={sessao.tentarNovamente}>
                Tentar novamente
              </button>
            </p>
          )}

          {cadastro && (
            <label className="campo">
              <span className="campo__rotulo">Nome</span>
              <input
                className="campo__entrada"
                value={nome}
                onChange={(e) => setNome(e.target.value)}
                autoComplete="name"
                minLength={2}
                maxLength={120}
                required
              />
            </label>
          )}

          <label className="campo">
            <span className="campo__rotulo">E-mail</span>
            <input
              className="campo__entrada"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              maxLength={254}
              required
            />
          </label>

          <div className="campo">
            <label htmlFor="senha" className="campo__rotulo">
              Senha
            </label>
            <input
              id="senha"
              className="campo__entrada"
              type="password"
              value={senha}
              onChange={(e) => setSenha(e.target.value)}
              autoComplete={cadastro ? 'new-password' : 'current-password'}
              minLength={cadastro ? 8 : 1}
              maxLength={128}
              required
              aria-describedby={cadastro ? 'senha-ajuda' : undefined}
            />
            {cadastro && (
              <span id="senha-ajuda" className="campo__ajuda">
                Mínimo de 8 caracteres.
              </span>
            )}
          </div>

          {erro && (
            <p className="alerta alerta--erro" role="alert">
              {erro}
            </p>
          )}

          <button type="submit" className="botao botao--primario botao--largo" disabled={enviando}>
            {enviando ? 'Aguarde…' : cadastro ? 'Criar conta' : 'Entrar'}
          </button>
        </form>
      </section>
    </div>
  )
}
