import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { ApiError, type Usuario } from '../api'
import { AreaContext } from '../contexto'
import { useNavegacao, type Pagina } from '../hooks/useNavegacao'
import { useRestaurantes } from '../hooks/useRestaurantes'
import type { StatusSistema } from '../hooks/useStatusSistema'
import { Categorias } from '../paginas/Categorias'
import { ContasPagar } from '../paginas/ContasPagar'
import { Despesas } from '../paginas/Despesas'
import { Equipe } from '../paginas/Equipe'
import { Documentos } from '../paginas/Documentos'
import { Fornecedores } from '../paginas/Fornecedores'
import { Inicio } from '../paginas/Inicio'
import { Relatorios } from '../paginas/Relatorios'
import { Cabecalho, Rodape } from './Cabecalho'
import { ChatWindow } from './ChatWindow'
import { FormRestaurante } from './FormRestaurante'
import { Icone } from './Icone'
import { Logo } from './Logo'
import { MenuLateral } from './MenuLateral'

interface AreaLogadaProps {
  usuario: Usuario
  status: StatusSistema
  onSair: () => void
  onSessaoExpirada: () => void
}

export function AreaLogada({ usuario, status, onSair, onSessaoExpirada }: AreaLogadaProps) {
  const restaurantes = useRestaurantes()
  const { pagina, irPara } = useNavegacao()
  const [criandoOutro, setCriandoOutro] = useState(false)
  // Gaveta do menu no celular; na tela grande o menu fica sempre à mostra.
  const [menuAberto, setMenuAberto] = useState(false)
  const { erro, selecionado } = restaurantes

  useEffect(() => {
    if (!menuAberto) return
    const aoTeclar = (evento: KeyboardEvent) => {
      if (evento.key === 'Escape') setMenuAberto(false)
    }
    window.addEventListener('keydown', aoTeclar)
    return () => window.removeEventListener('keydown', aoTeclar)
  }, [menuAberto])

  const sessaoExpirada = erro instanceof ApiError && erro.status === 401
  useEffect(() => {
    if (sessaoExpirada) onSessaoExpirada()
  }, [sessaoExpirada, onSessaoExpirada])

  const { recarregar } = restaurantes
  const contexto = useMemo(
    () =>
      selecionado
        ? { restaurante: selecionado, sessaoExpirou: onSessaoExpirada, recarregarRestaurantes: recarregar }
        : null,
    [selecionado, onSessaoExpirada, recarregar],
  )

  // Telas sem restaurante escolhido: topo simples, sem barra lateral.
  const semMenu = (conteudo: ReactNode) => (
    <>
      <Cabecalho status={status} usuario={usuario} onSair={onSair} />
      <main className="conteudo">{conteudo}</main>
      <Rodape />
    </>
  )

  if (restaurantes.carregando) {
    // Sem cabeçalho: ele piscaria na tela por um instante antes de a barra lateral aparecer.
    return (
      <main className="conteudo">
        <p className="carregando-pagina">Carregando restaurantes…</p>
      </main>
    )
  }

  if (erro) {
    return semMenu(
      <p className="alerta alerta--erro" role="alert">
        Não foi possível carregar seus restaurantes. {erro instanceof Error ? erro.message : ''}{' '}
        <button type="button" className="link" onClick={restaurantes.recarregar}>
          Tentar novamente
        </button>
      </p>,
    )
  }

  if (!contexto || criandoOutro) {
    return semMenu(
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
      />,
    )
  }

  const { restaurante } = contexto

  function conteudo(atual: Pagina) {
    switch (atual) {
      case 'despesas':
        return <Despesas />
      case 'contas':
        return <ContasPagar />
      case 'documentos':
        return <Documentos />
      case 'relatorios':
        return <Relatorios />
      case 'fornecedores':
        return <Fornecedores />
      case 'categorias':
        return <Categorias />
      case 'equipe':
        return <Equipe />
      case 'assistente':
        return <ChatWindow statusIA={status.ia} onFalha={status.atualizar} onSessaoExpirada={onSessaoExpirada} />
      default:
        return <Inicio irPara={irPara} />
    }
  }

  return (
    <AreaContext.Provider value={contexto}>
      <div className="app-com-menu">
        <div className="barra-movel">
          <button
            type="button"
            className="barra-movel__menu"
            aria-label="Abrir menu"
            aria-expanded={menuAberto}
            aria-controls="menu-lateral"
            onClick={() => setMenuAberto(true)}
          >
            <Icone nome="menu" tamanho={24} />
          </button>
          <Logo tamanho={28} />
          <span className="barra-movel__nome">{restaurante.nome}</span>
        </div>

        {menuAberto && (
          <button
            type="button"
            className="menu-lateral__fundo"
            aria-label="Fechar menu"
            tabIndex={-1}
            onClick={() => setMenuAberto(false)}
          />
        )}

        <MenuLateral
          pagina={pagina}
          restaurantes={restaurantes.restaurantes}
          restaurante={restaurante}
          onSelecionarRestaurante={restaurantes.selecionar}
          onNovoRestaurante={() => {
            setMenuAberto(false)
            setCriandoOutro(true)
          }}
          usuario={usuario}
          status={status}
          onSair={onSair}
          aberto={menuAberto}
          onFechar={() => setMenuAberto(false)}
        />

        <div className="app-com-menu__conteudo">
          {/* key: ao trocar de restaurante, a página recomeça do zero (filtros, formulários, conversa). */}
          <main key={restaurante.id} className="area-logada__pagina">
            {conteudo(pagina)}
          </main>
          <Rodape />
        </div>
      </div>
    </AreaContext.Provider>
  )
}
