import { useState } from 'react'
import { useArea } from '../contexto'
import { useAcao } from '../hooks/useAcao'
import { useCarregar } from '../hooks/useCarregar'
import { listarContas, pagarConta, type ContaPagar } from '../recursos/financeiro'
import { formatarData, formatarMoeda, hojeIso } from '../utils/formato'

const QUANTIDADE = 5

const SITUACOES = { vencida: 'Vencida', vence_hoje: 'Vence hoje', a_vencer: 'A vencer', paga: 'Paga' } as const

interface ProximasContasProps {
  /** Avisa o painel que um pagamento mudou os totais (vencimentos e despesas do mês). */
  onPagamento: () => void
  onVerTodas: () => void
}

/** As próximas contas pendentes, com pagamento ali mesmo (confirmado na própria linha). */
export function ProximasContas({ onPagamento, onVerTodas }: ProximasContasProps) {
  const { restaurante } = useArea()
  const lista = useCarregar(`proximas-${restaurante.id}`, () =>
    listarContas(restaurante.id, { situacao: 'pendentes', limite: QUANTIDADE, deslocamento: 0 }),
  )
  const { executar, ocupado, erro } = useAcao()
  const [confirmando, setConfirmando] = useState<number | null>(null)

  function pagar(conta: ContaPagar) {
    void executar(
      () => pagarConta(restaurante.id, conta.id, hojeIso()),
      () => {
        setConfirmando(null)
        lista.recarregar()
        onPagamento()
      },
    )
  }

  const contas = lista.dados?.itens ?? []
  const restantes = (lista.dados?.total ?? 0) - contas.length

  return (
    <section className="cartao proximas-contas" aria-labelledby="titulo-proximas-contas">
      <h3 id="titulo-proximas-contas" className="inicio__titulo-secao">
        Próximas contas
      </h3>

      {(lista.erro || erro) && (
        <p className="alerta alerta--erro" role="alert">
          {erro ?? lista.erro}
        </p>
      )}

      {lista.dados && contas.length === 0 && <p className="vazio">Nenhuma conta pendente. Tudo em dia!</p>}

      {contas.length > 0 && (
        <ul className="proximas-contas__lista">
          {contas.map((c) => (
            <li key={c.id} className="proximas-contas__item">
              <div className="proximas-contas__info">
                <span className="proximas-contas__descricao" title={c.descricao}>
                  {c.descricao}
                </span>
                <span className="proximas-contas__data">
                  <span className={`situacao situacao--${c.situacao}`}>{SITUACOES[c.situacao]}</span>
                  {formatarData(c.data_vencimento)}
                </span>
              </div>
              <span className="proximas-contas__valor">{formatarMoeda(c.valor)}</span>
              {confirmando === c.id ? (
                <span
                  className="proximas-contas__confirmar"
                  role="group"
                  aria-label={`Confirmar pagamento de ${c.descricao}`}
                >
                  <span>Pagar hoje?</span>
                  <button
                    type="button"
                    className="botao botao--primario botao--pequeno"
                    disabled={ocupado}
                    onClick={() => pagar(c)}
                  >
                    Confirmar
                  </button>
                  <button type="button" className="link" disabled={ocupado} onClick={() => setConfirmando(null)}>
                    Cancelar
                  </button>
                </span>
              ) : (
                <button
                  type="button"
                  className="botao botao--secundario botao--pequeno"
                  aria-label={`Pagar ${c.descricao}`}
                  disabled={ocupado}
                  onClick={() => setConfirmando(c.id)}
                >
                  Pagar
                </button>
              )}
            </li>
          ))}
        </ul>
      )}

      <footer className="painel-despesas__rodape">
        <button type="button" className="link" onClick={onVerTodas}>
          {restantes > 0 ? `Ver todas as contas (+${restantes})` : 'Ver todas as contas'}
        </button>
      </footer>
    </section>
  )
}
