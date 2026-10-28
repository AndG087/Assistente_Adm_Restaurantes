import { useRef, useState, type ChangeEvent } from 'react'
import { ApiError } from '../api'
import { DetalheDocumento } from '../components/DetalheDocumento'
import { Icone } from '../components/Icone'
import { useArea } from '../contexto'
import { useCarregar } from '../hooks/useCarregar'
import {
  enviarDocumento,
  listarDocumentos,
  type Documento,
  type DocumentoDetalhe,
  type StatusDocumento,
} from '../recursos/documentos'
import { STATUS } from '../utils/documentos'
import { formatarData, formatarMoeda } from '../utils/formato'

const ABAS: Record<StatusDocumento | 'todos', string> = {
  pendente: 'A conferir',
  erro: 'Com erro',
  concluido: 'Conferidos',
  descartado: 'Descartados',
  todos: 'Todos',
}

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
  const campoCamera = useRef<HTMLInputElement>(null)

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
        <div className="documentos__envio">
          {/* No celular, abre direto a câmera traseira (a foto chega como JPG, formato aceito). */}
          <input
            ref={campoCamera}
            type="file"
            accept="image/jpeg,image/png"
            capture="environment"
            className="visualmente-oculto"
            aria-label="Fotografar nota ou boleto"
            onChange={(e) => void aoEscolherArquivos(e)}
          />
          <button
            type="button"
            className="botao botao--secundario so-celular"
            disabled={enviando}
            onClick={() => campoCamera.current?.click()}
          >
            <Icone nome="camera" tamanho={18} />
            Fotografar nota
          </button>
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
