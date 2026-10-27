import { useEffect, useState } from 'react'
import { ApiError, type IAStatusResponse } from '../api'
import { useRestaurantes } from '../hooks/useRestaurantes'
import { ChatWindow } from './ChatWindow'
import { FormRestaurante } from './FormRestaurante'

interface AreaLogadaProps {
  statusIA: IAStatusResponse | null
  onFalhaIA: () => void
  onSessaoExpirada: () => void
}

function formatarCnpj(cnpj: string): string {
  return cnpj.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/, '$1.$2.$3/$4-$5')
}

const PAPEIS = { proprietario: 'Proprietário', membro: 'Membro' } as const

export function AreaLogada({ statusIA, onFalhaIA, onSessaoExpirada }: AreaLogadaProps) {
  const restaurantes = useRestaurantes()
  const [criandoOutro, setCriandoOutro] = useState(false)
  const { erro, selecionado } = restaurantes

  const sessaoExpirada = erro instanceof ApiError && erro.status === 401
  useEffect(() => {
    if (sessaoExpirada) onSessaoExpirada()
  }, [sessaoExpirada, onSessaoExpirada])

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

  if (!selecionado || criandoOutro) {
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

  return (
    <div className="area-logada">
      <section className="cartao restaurante-atual" aria-label="Restaurante selecionado">
        <label className="campo campo--em-linha">
          <span className="campo__rotulo">Restaurante</span>
          <select
            className="campo__entrada"
            value={selecionado.id}
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
            <dd>{selecionado.cnpj ? formatarCnpj(selecionado.cnpj) : 'Não informado'}</dd>
          </div>
          <div>
            <dt>Seu papel</dt>
            <dd>{PAPEIS[selecionado.papel]}</dd>
          </div>
        </dl>
        <button type="button" className="botao botao--secundario" onClick={() => setCriandoOutro(true)}>
          Novo restaurante
        </button>
      </section>

      <ChatWindow statusIA={statusIA} onFalha={onFalhaIA} onSessaoExpirada={onSessaoExpirada} />
    </div>
  )
}
