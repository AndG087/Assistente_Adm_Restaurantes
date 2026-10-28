import { useRef, useState, type ChangeEvent } from 'react'
import { ApiError } from '../api'
import { useArea } from '../contexto'
import { useCarregar } from '../hooks/useCarregar'
import {
  enviarDocumento,
  excluirDocumento,
  listarDocumentos,
  obterDocumento,
  reprocessarDocumento,
  urlDoArquivo,
  type Documento,
  type DocumentoDetalhe,
  type StatusDocumento,
} from '../recursos/documentos'
import { formatarData, formatarDocumento, formatarMoeda } from '../utils/formato'

const ABAS: Record<StatusDocumento | 'todos', string> = {
  pendente: 'A conferir',
  erro: 'Com erro',
  concluido: 'Conferidos',
  descartado: 'Descartados',
  todos: 'Todos',
}

const STATUS: Record<StatusDocumento, string> = {
  pendente: 'A conferir',
  erro: 'Erro na leitura',
  concluido: 'Conferido',
  descartado: 'Descartado',
}

const METODOS = { pdf_texto: 'Texto do PDF', ocr: 'OCR' } as const

function dataDeEnvio(iso: string): string {
  return formatarData(iso.slice(0, 10))
}

export function Documentos() {
  const { restaurante, mensagemDeErro } = useArea()
  const [aba, setAba] = useState<StatusDocumento | 'todos'>('pendente')
  const [abertoId, setAbertoId] = useState<number | null>(null)
  const [enviando, setEnviando] = useState(false)
  const [aviso, setAviso] = useState<{ tipo: 'erro' | 'ok'; texto: string } | null>(null)
  const campoArquivo = useRef<HTMLInputElement>(null)

  const lista = useCarregar(`${restaurante.id}|${aba}`, () =>
    listarDocumentos(restaurante.id, aba === 'todos' ? null : aba),
  )

  async function aoEscolherArquivos(evento: ChangeEvent<HTMLInputElement>) {
    const arquivos = Array.from(evento.target.files ?? [])
    evento.target.value = '' // permite escolher o mesmo arquivo de novo
    if (arquivos.length === 0) return
    setEnviando(true)
    setAviso(null)
    const erros: string[] = []
    let ultimo: DocumentoDetalhe | null = null
    // Um por vez: cada envio já extrai o texto (OCR pode levar alguns segundos).
    for (const arquivo of arquivos) {
      try {
        ultimo = await enviarDocumento(restaurante.id, arquivo)
      } catch (e) {
        const repetido = e instanceof ApiError && e.status === 409
        erros.push(`${arquivo.name}: ${repetido ? (e as ApiError).message : mensagemDeErro(e)}`)
      }
    }
    setEnviando(false)
    lista.recarregar()
    if (erros.length) {
      setAviso({ tipo: 'erro', texto: erros.join(' ') })
    } else if (arquivos.length === 1 && ultimo) {
      setAbertoId(ultimo.id)
    } else {
      setAviso({ tipo: 'ok', texto: `${arquivos.length} documentos enviados.` })
    }
  }

  if (abertoId !== null) {
    return (
      <DetalheDocumento
        id={abertoId}
        onFechar={() => {
          setAbertoId(null)
          lista.recarregar()
        }}
      />
    )
  }

  return (
    <section className="pagina-secao" aria-labelledby="titulo-documentos">
      <header className="pagina-secao__cabecalho">
        <h2 id="titulo-documentos">Documentos</h2>
        <div>
          <input
            ref={campoArquivo}
            type="file"
            accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png"
            multiple
            className="visualmente-oculto"
            aria-label="Escolher documentos"
            onChange={(e) => void aoEscolherArquivos(e)}
          />
          <button
            type="button"
            className="botao botao--primario"
            disabled={enviando}
            onClick={() => campoArquivo.current?.click()}
          >
            {enviando ? 'Enviando e lendo…' : 'Enviar documentos'}
          </button>
        </div>
      </header>

      <p className="pagina-secao__ajuda">
        Envie notas fiscais, boletos ou comprovantes em PDF, JPG ou PNG (até 10 MB). O texto é lido neste computador,
        sem enviar nada para a internet; depois você confere os dados e gera a despesa ou a conta a pagar.
      </p>

      {aviso && (
        <p className={`alerta ${aviso.tipo === 'erro' ? 'alerta--erro' : 'alerta--ok'}`} role={aviso.tipo === 'erro' ? 'alert' : 'status'}>
          {aviso.texto}
        </p>
      )}

      <div className="cartao filtros">
        <div className="segmentos" role="group" aria-label="Situação">
          {(Object.keys(ABAS) as (keyof typeof ABAS)[]).map((chave) => (
            <button
              key={chave}
              type="button"
              className="segmentos__item"
              aria-pressed={aba === chave}
              onClick={() => setAba(chave)}
            >
              {ABAS[chave]}
            </button>
          ))}
        </div>
      </div>

      {lista.erro && (
        <p className="alerta alerta--erro" role="alert">
          {lista.erro}
        </p>
      )}

      {lista.dados && (
        <div className="cartao tabela-container" aria-busy={lista.carregando}>
          {lista.dados.length === 0 ? (
            <p className="vazio">Nenhum documento nesta situação.</p>
          ) : (
            <table className="tabela">
              <thead>
                <tr>
                  <th scope="col">Enviado em</th>
                  <th scope="col">Arquivo</th>
                  <th scope="col">Situação</th>
                  <th scope="col" className="tabela__numero">
                    Valor encontrado
                  </th>
                  <th scope="col">
                    <span className="visualmente-oculto">Ações</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {lista.dados.map((d) => (
                  <LinhaDocumento key={d.id} documento={d} onAbrir={() => setAbertoId(d.id)} />
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </section>
  )
}

function LinhaDocumento({ documento: d, onAbrir }: { documento: Documento; onAbrir: () => void }) {
  return (
    <tr>
      <td data-rotulo="Enviado em">{dataDeEnvio(d.criado_em)}</td>
      <td data-rotulo="Arquivo">
        {d.nome_original}
        {d.erro && <span className="tabela__detalhe">{d.erro}</span>}
      </td>
      <td data-rotulo="Situação">
        <span className={`situacao situacao--doc-${d.status}`}>{STATUS[d.status]}</span>
      </td>
      <td data-rotulo="Valor encontrado" className="tabela__numero">
        {d.dados_extraidos?.valor ? formatarMoeda(d.dados_extraidos.valor) : <span className="suave">—</span>}
      </td>
      <td className="tabela__acoes">
        <button type="button" className="link" onClick={onAbrir} aria-label={`Abrir ${d.nome_original}`}>
          {d.status === 'pendente' ? 'Conferir' : 'Abrir'}
        </button>
      </td>
    </tr>
  )
}

interface DetalheDocumentoProps {
  id: number
  onFechar: () => void
}

function DetalheDocumento({ id, onFechar }: DetalheDocumentoProps) {
  const { restaurante, mensagemDeErro } = useArea()
  const doc = useCarregar(`doc-${restaurante.id}-${id}`, () => obterDocumento(restaurante.id, id))
  const [erroAcao, setErroAcao] = useState<string | null>(null)
  const [ocupado, setOcupado] = useState(false)

  async function executar(acao: () => Promise<unknown>, depois: () => void) {
    setErroAcao(null)
    setOcupado(true)
    try {
      await acao()
      depois()
    } catch (e) {
      setErroAcao(mensagemDeErro(e))
    } finally {
      setOcupado(false)
    }
  }

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
