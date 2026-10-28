import { useEffect, useMemo, useState } from 'react'
import { ApiError, type IAStatusResponse } from '../api'
import { AreaContext } from '../contexto'
import { PAGINAS, useNavegacao, type Pagina } from '../hooks/useNavegacao'
import { useRestaurantes } from '../hooks/useRestaurantes'
import { Categorias } from '../paginas/Categorias'
import { ContasPagar } from '../paginas/ContasPagar'
import { Despesas } from '../paginas/Despesas'
import { Fornecedores } from '../paginas/Fornecedores'
import { Inicio } from '../paginas/Inicio'
import { formatarDocumento } from '../utils/formato'
import { ChatWindow } from './ChatWindow'
import { FormRestaurante } from './FormRestaurante'

interface AreaLogadaProps {
  statusIA: IAStatusResponse | null
  onFalhaIA: () => void
  onSessaoExpirada: () => void
}

const PAPEIS = { proprietario: 'Proprietário', membro: 'Membro' } as const

export function AreaLogada({ statusIA, onFalhaIA, onSessaoExpirada }: AreaLogadaProps) {
  const restaurantes = useRestaurantes()
  const { pagina, irPara } = useNavegacao()
  const [criandoOutro, setCriandoOutro] = useState(false)
  const { erro, selecionado } = restaurantes

  const sessaoExpirada = erro instanceof ApiError && erro.status === 401
  useEffect(() => {
    if (sessaoExpirada) onSessaoExpirada()
  }, [sessaoExpirada, onSessaoExpirada])

  const contexto = useMemo(
    () => (selecionado ? { restaurante: selecionado, sessaoExpirou: onSessaoExpirada } : null),
    [selecionado, onSessaoExpirada],
  )

  if (restaurantes.carregando) {
    return <p className="carregando-pagina">Carregando restaurantes…</p>
  }

  if (erro) {
    return (
      <p className="alerta alerta--erro" role="alert">
        Não foi possível carregar seus restaurantes. {erro instanceof Error ? erro.message : ''}{' '}
        <button type="button" className="link" onClick={restaurantes.recarregar}>
          Tentar novamente
        </button>
      </p>
    )
  }

  if (!contexto || criandoOutro) {
    return (
      <FormRestaurante
        titulo={selecionado ? 'Novo restaurante' : 'Cadastre seu restaurante'}
        descricao={
          selecionado
            ? undefined
            : 'Para começar, informe o restaurante que você administra. Os dados de cada restaurante ficam separados.'
        }
        onCriar={async (nome, cnpj) => {
          await restaurantes.criar(nome, cnpj)
          setCriandoOutro(false)
        }}
        onCancelar={selecionado ? () => setCriandoOutro(false) : undefined}
      />
    )
  }

  const { restaurante } = contexto

  function conteudo(atual: Pagina) {
    switch (atual) {
      case 'despesas':
        return <Despesas />
      case 'contas':
        return <ContasPagar />
      case 'fornecedores':
        return <Fornecedores />
      case 'categorias':
        return <Categorias />
      case 'assistente':
        return <ChatWindow statusIA={statusIA} onFalha={onFalhaIA} onSessaoExpirada={onSessaoExpirada} />
      default:
        return <Inicio irPara={irPara} />
    }
  }

  return (
    <AreaContext.Provider value={contexto}>
      <div className="area-logada">
        <section className="cartao restaurante-atual" aria-label="Restaurante selecionado">
          <label className="campo campo--em-linha">
            <span className="campo__rotulo">Restaurante</span>
            <select
              className="campo__entrada"
              value={restaurante.id}
              onChange={(e) => restaurantes.selecionar(Number(e.target.value))}
            >
              {restaurantes.restaurantes.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.nome}
                </option>
              ))}
            </select>
          </label>
          <dl className="restaurante-atual__dados">
            <div>
              <dt>CNPJ</dt>
              <dd>{restaurante.cnpj ? formatarDocumento(restaurante.cnpj) : 'Não informado'}</dd>
            </div>
            <div>
              <dt>Seu papel</dt>
              <dd>{PAPEIS[restaurante.papel]}</dd>
            </div>
          </dl>
          <button type="button" className="botao botao--secundario" onClick={() => setCriandoOutro(true)}>
            Novo restaurante
          </button>
        </section>

        <nav className="menu" aria-label="Seções">
          {(Object.keys(PAGINAS) as Pagina[]).map((chave) => (
            <a
              key={chave}
              href={`#/${chave}`}
              className="menu__item"
              aria-current={pagina === chave ? 'page' : undefined}
            >
              {PAGINAS[chave]}
            </a>
          ))}
        </nav>

        {/* key: ao trocar de restaurante, a página recomeça do zero (filtros, formulários, conversa). */}
        <div key={restaurante.id} className="area-logada__pagina">
          {conteudo(pagina)}
        </div>
      </div>
    </AreaContext.Provider>
  )
}
