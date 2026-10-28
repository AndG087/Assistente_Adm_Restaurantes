import { useArea } from '../contexto'
import { useCarregar } from '../hooks/useCarregar'
import { totaisPorFornecedor } from '../recursos/relatorios'
import type { Periodo } from '../utils/formato'
import { formatarMoeda } from '../utils/formato'
import { BarrasTotais } from './BarrasTotais'

const QUANTIDADE = 5

interface MaioresFornecedoresProps {
  periodo: Periodo
  onVerRelatorios: () => void
}

/**
 * Com quem o restaurante mais gastou no período. As despesas sem fornecedor não entram no ranking
 * (não são "um fornecedor"), mas o valor delas aparece abaixo: é dinheiro que o dono não sabe para quem foi.
 */
export function MaioresFornecedores({ periodo, onVerRelatorios }: MaioresFornecedoresProps) {
  const { restaurante } = useArea()
  const totais = useCarregar(`fornecedores-${restaurante.id}-${periodo.de}-${periodo.ate}`, () =>
    totaisPorFornecedor(restaurante.id, periodo.de, periodo.ate),
  )

  const lista = totais.dados ?? []
  const comFornecedor = lista.filter((t) => t.fornecedor !== null).slice(0, QUANTIDADE)
  const semFornecedor = lista.find((t) => t.fornecedor === null)

  return (
    <section className="cartao painel-lateral" aria-labelledby="titulo-maiores-fornecedores">
      <h3 id="titulo-maiores-fornecedores" className="inicio__titulo-secao">
        Maiores fornecedores do mês
      </h3>

      {totais.erro && (
        <p className="alerta alerta--erro" role="alert">
          {totais.erro}
        </p>
      )}

      {totais.dados && comFornecedor.length === 0 && (
        <p className="vazio">Nenhuma despesa com fornecedor informado neste mês.</p>
      )}

      {comFornecedor.length > 0 && (
        <BarrasTotais
          rotulo="Maiores fornecedores do mês"
          itens={comFornecedor.map((t) => ({
            chave: String(t.fornecedor?.id),
            nome: t.fornecedor?.nome ?? '',
            valor: t.valor_total,
          }))}
        />
      )}

      {semFornecedor && (
        <p className="painel-lateral__nota">
          Mais <strong>{formatarMoeda(semFornecedor.valor_total)}</strong> em despesas sem fornecedor informado.
        </p>
      )}

      <footer className="painel-despesas__rodape">
        <button type="button" className="link" onClick={onVerRelatorios}>
          Ver relatórios
        </button>
      </footer>
    </section>
  )
}
