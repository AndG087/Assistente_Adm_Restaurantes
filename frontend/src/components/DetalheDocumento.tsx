import { useArea } from '../contexto'
import { useAcao } from '../hooks/useAcao'
import { useCarregar } from '../hooks/useCarregar'
import { excluirDocumento, obterDocumento, reprocessarDocumento, urlDoArquivo } from '../recursos/documentos'
import { STATUS } from '../utils/documentos'
import { formatarData, formatarDocumento, formatarMoeda } from '../utils/formato'
import { ConferenciaDocumento } from './ConferenciaDocumento'

const METODOS = { pdf_texto: 'Texto do PDF', ocr: 'OCR' } as const

interface DetalheDocumentoProps {
  id: number
  onFechar: () => void
}

export function DetalheDocumento({ id, onFechar }: DetalheDocumentoProps) {
  const { restaurante } = useArea()
  const doc = useCarregar(`doc-${restaurante.id}-${id}`, () => obterDocumento(restaurante.id, id))
  const { executar, ocupado, erro: erroAcao } = useAcao()

  if (!doc.dados) {
    return doc.erro ? (
      <p className="alerta alerta--erro" role="alert">
        {doc.erro}
      </p>
    ) : (
      <p className="carregando-pagina">Carregando documento…</p>
    )
  }

  const d = doc.dados
  const dados = d.dados_extraidos
  const arquivo = urlDoArquivo(restaurante.id, d.id)

  return (
    <section className="pagina-secao" aria-labelledby="titulo-documento">
      <header className="pagina-secao__cabecalho">
        <h2 id="titulo-documento">{d.nome_original}</h2>
        <button type="button" className="botao botao--secundario" onClick={onFechar}>
          Voltar
        </button>
      </header>

      {erroAcao && (
        <p className="alerta alerta--erro" role="alert">
          {erroAcao}
        </p>
      )}

      <div className="conferencia">
        <div className="cartao conferencia__arquivo">
          {d.tipo_mime === 'application/pdf' ? (
            <iframe src={arquivo} title={`Visualização de ${d.nome_original}`} />
          ) : (
            <img src={arquivo} alt={`Imagem de ${d.nome_original}`} />
          )}
        </div>

        <div className="conferencia__lado">
          <div className="cartao conferencia__info">
            <p>
              <span className={`situacao situacao--doc-${d.status}`}>{STATUS[d.status]}</span>
              {d.metodo_extracao && <span className="etiqueta">{METODOS[d.metodo_extracao]}</span>}
            </p>
            {d.erro && (
              <p className="alerta alerta--erro" role="alert">
                {d.erro}
              </p>
            )}
            {dados && (
              <dl className="dados-extraidos">
                <div>
                  <dt>Valor</dt>
                  <dd>{dados.valor ? formatarMoeda(dados.valor) : '—'}</dd>
                </div>
                <div>
                  <dt>Emissão</dt>
                  <dd>{dados.data_emissao ? formatarData(dados.data_emissao) : '—'}</dd>
                </div>
                <div>
                  <dt>Vencimento</dt>
                  <dd>{dados.data_vencimento ? formatarData(dados.data_vencimento) : '—'}</dd>
                </div>
                <div>
                  <dt>CNPJ do emitente</dt>
                  <dd>{dados.cnpj_emitente ? formatarDocumento(dados.cnpj_emitente) : '—'}</dd>
                </div>
                <div>
                  <dt>Nº do documento</dt>
                  <dd>{dados.numero_documento ?? '—'}</dd>
                </div>
              </dl>
            )}
            <div className="formulario__acoes">
              {(d.status === 'pendente' || d.status === 'erro') && (
                <button
                  type="button"
                  className="botao botao--secundario"
                  disabled={ocupado}
                  onClick={() => void executar(() => reprocessarDocumento(restaurante.id, d.id), doc.recarregar)}
                >
                  Ler novamente
                </button>
              )}
              {d.status !== 'concluido' && (
                <button
                  type="button"
                  className="botao botao--secundario link--perigo"
                  disabled={ocupado}
                  onClick={() => {
                    if (window.confirm(`Excluir "${d.nome_original}"? O arquivo será apagado.`))
                      void executar(() => excluirDocumento(restaurante.id, d.id), onFechar)
                  }}
                >
                  Excluir
                </button>
              )}
            </div>
          </div>

          {(d.status === 'pendente' || d.status === 'erro') && (
            <ConferenciaDocumento documento={d} onConcluir={onFechar} />
          )}
          {d.status === 'concluido' && (
            <p className="alerta alerta--ok" role="status">
              Documento conferido: gerou {d.despesa_id ? 'uma despesa' : d.conta_pagar_id ? 'uma conta a pagar' : 'um lançamento (já removido)'}.
            </p>
          )}

          {d.texto_extraido && (
            <details className="cartao conferencia__texto">
              <summary>Texto lido do documento</summary>
              <pre>{d.texto_extraido}</pre>
            </details>
          )}
        </div>
      </div>
    </section>
  )
}
