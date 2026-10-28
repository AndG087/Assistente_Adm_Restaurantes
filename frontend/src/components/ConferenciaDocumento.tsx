import { useState } from 'react'
import { useArea } from '../contexto'
import { useAcao } from '../hooks/useAcao'
import { useCarregar } from '../hooks/useCarregar'
import { salvarFornecedor } from '../recursos/cadastros'
import {
  confirmarDocumento,
  descartarDocumento,
  obterConferencia,
  type DocumentoDetalhe,
} from '../recursos/documentos'
import { formatarData, formatarDocumento, formatarMoeda, hojeIso } from '../utils/formato'
import { FormLancamento, type LancamentoInicial } from './FormLancamento'

type Tipo = 'despesa' | 'conta'

const TIPOS_DUPLICADO = { despesa: 'Despesa', conta: 'Conta', documento: 'Documento' } as const

interface ConferenciaDocumentoProps {
  documento: DocumentoDetalhe
  onConcluir: () => void
}

/** Formulário preenchido com o que foi lido no documento; o usuário confere e gera o lançamento. */
export function ConferenciaDocumento({ documento, onConcluir }: ConferenciaDocumentoProps) {
  const { restaurante, mensagemDeErro } = useArea()
  const dados = documento.dados_extraidos
  const [tipo, setTipo] = useState<Tipo>(dados?.tipo_sugerido === 'conta' ? 'conta' : 'despesa')
  const conferencia = useCarregar(`conf-${restaurante.id}-${documento.id}`, () =>
    obterConferencia(restaurante.id, documento.id),
  )
  // Fornecedor cadastrado aqui mesmo, a partir do CNPJ encontrado.
  const [fornecedorCriado, setFornecedorCriado] = useState<{ id: number; nome: string } | null>(null)
  const [erro, setErro] = useState<string | null>(null)

  if (conferencia.carregando && !conferencia.dados) {
    return <p className="carregando-pagina">Preparando a conferência…</p>
  }

  const fornecedor = fornecedorCriado ?? conferencia.dados?.fornecedor_sugerido ?? null
  const duplicados = conferencia.dados?.possiveis_duplicados ?? []
  const numero = dados?.numero_documento
  const inicial: LancamentoInicial = {
    descricao: [numero ? `NF ${numero}` : null, fornecedor?.nome].filter(Boolean).join(' - ') ||
      documento.nome_original.replace(/\.[^.]+$/, ''),
    valor: dados?.valor ?? '',
    data:
      (tipo === 'conta' ? dados?.data_vencimento : dados?.data_emissao) ??
      dados?.data_vencimento ??
      dados?.data_emissao ??
      hojeIso(),
    categoria: null,
    fornecedor,
    numero_documento: numero ?? null,
    observacoes: null,
  }

  async function descartar() {
    if (!window.confirm('Descartar este documento? Nenhum lançamento será criado.')) return
    try {
      await descartarDocumento(restaurante.id, documento.id)
      onConcluir()
    } catch (e) {
      setErro(mensagemDeErro(e))
    }
  }

  const seletorTipo = (
    <div className="segmentos" role="group" aria-label="Gerar como">
      {(['despesa', 'conta'] as const).map((opcao) => (
        <button
          key={opcao}
          type="button"
          className="segmentos__item"
          aria-pressed={tipo === opcao}
          onClick={() => setTipo(opcao)}
        >
          {opcao === 'despesa' ? 'Despesa (já paga)' : 'Conta a pagar'}
        </button>
      ))}
    </div>
  )

  return (
    <>
      {duplicados.length > 0 && (
        <div className="cartao duplicados" role="alert">
          <strong>Este documento pode já ter sido lançado:</strong>
          <ul>
            {duplicados.map((d) => (
              <li key={`${d.tipo}-${d.id}`}>
                {TIPOS_DUPLICADO[d.tipo]} “{d.descricao}”
                {d.valor && ` · ${formatarMoeda(d.valor)}`}
                {d.data && ` · ${formatarData(d.data)}`} — {d.motivo}
              </li>
            ))}
          </ul>
          <span>Confira antes de continuar. Se for o mesmo, descarte este documento.</span>
        </div>
      )}

      {dados?.cnpj_emitente && !fornecedor && conferencia.dados && (
        <NovoFornecedor
          cnpj={dados.cnpj_emitente}
          onCriado={(novo) => setFornecedorCriado(novo)}
        />
      )}

      {erro && (
        <p className="alerta alerta--erro" role="alert">
          {erro}
        </p>
      )}

      {/* key: ao reconhecer/cadastrar o fornecedor, o formulário recomeça já com ele selecionado. */}
      <FormLancamento
        key={fornecedor?.id ?? 'sem-fornecedor'}
        titulo="Conferir e lançar"
        rotuloData={tipo === 'conta' ? 'Vencimento' : 'Data da despesa'}
        inicial={inicial}
        cabecalho={seletorTipo}
        rotuloSalvar={tipo === 'conta' ? 'Criar conta a pagar' : 'Criar despesa'}
        rotuloCancelar="Descartar documento"
        onCancelar={() => void descartar()}
        onSalvar={async (campos, data) => {
          await confirmarDocumento(restaurante.id, documento.id, { ...campos, tipo, data })
          onConcluir()
        }}
      />
    </>
  )
}

function NovoFornecedor({ cnpj, onCriado }: { cnpj: string; onCriado: (f: { id: number; nome: string }) => void }) {
  const { restaurante } = useArea()
  const [nome, setNome] = useState('')
  const { executar, ocupado, erro } = useAcao()

  function cadastrar() {
    return executar(async () => {
      const novo = await salvarFornecedor(restaurante.id, null, {
        nome,
        documento: cnpj,
        telefone: null,
        email: null,
        observacoes: null,
        ativo: true,
      })
      onCriado({ id: novo.id, nome: novo.nome })
    })
  }

  return (
    <div className="cartao conferencia__info">
      <p>
        O CNPJ <strong>{formatarDocumento(cnpj)}</strong> não é de nenhum fornecedor cadastrado.
      </p>
      <div className="filtros filtros--sem-borda">
        <label className="campo">
          <span className="campo__rotulo">Nome do fornecedor</span>
          <input className="campo__entrada" value={nome} onChange={(e) => setNome(e.target.value)} maxLength={150} />
        </label>
        <button
          type="button"
          className="botao botao--secundario"
          disabled={ocupado || nome.trim().length < 2}
          onClick={() => void cadastrar()}
        >
          {ocupado ? 'Cadastrando…' : 'Cadastrar fornecedor'}
        </button>
      </div>
      {erro && (
        <p className="alerta alerta--erro" role="alert">
          {erro}
        </p>
      )}
    </div>
  )
}
