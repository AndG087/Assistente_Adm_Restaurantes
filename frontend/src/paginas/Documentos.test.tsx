import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { chamadas, json, renderizarNaArea, simularBackend } from '../test/backendFalso'
import { Documentos } from './Documentos'

const DADOS = {
  valor: '1234.56',
  data_emissao: '2026-10-05',
  data_vencimento: null,
  cnpj_emitente: '11222333000181',
  numero_documento: '4521',
  chave_acesso: null,
  tipo_sugerido: 'despesa',
}

function documento(campos: Record<string, unknown> = {}) {
  return {
    id: 1,
    nome_original: 'nota.pdf',
    tipo_mime: 'application/pdf',
    tamanho_bytes: 1000,
    status: 'pendente',
    metodo_extracao: 'pdf_texto',
    erro: null,
    dados_extraidos: DADOS,
    despesa_id: null,
    conta_pagar_id: null,
    criado_em: '2026-10-20T12:00:00',
    texto_extraido: 'VALOR TOTAL DA NOTA 1.234,56',
    ...campos,
  }
}

describe('Documentos', () => {
  it('lista os documentos a conferir com o valor encontrado', async () => {
    const fetchFalso = simularBackend({ 'GET /api/restaurantes/10/documentos': () => json([documento()]) })

    renderizarNaArea(<Documentos />)

    const linha = (await screen.findByText('nota.pdf')).closest('tr')!
    expect(within(linha).getByText(/R\$\s1\.234,56/)).toBeInTheDocument()
    expect(within(linha).getByRole('button', { name: 'Abrir nota.pdf' })).toHaveTextContent('Conferir')
    expect(chamadas(fetchFalso, 'GET', '/api/restaurantes/10/documentos')[0].url.searchParams.get('status')).toBe(
      'pendente',
    )
  })

  it('envia o arquivo como formulário e abre o documento enviado', async () => {
    const fetchFalso = simularBackend({
      'GET /api/restaurantes/10/documentos': () => json([]),
      'POST /api/restaurantes/10/documentos': () => json(documento(), 201),
      'GET /api/restaurantes/10/documentos/1': () => json(documento()),
    })
    renderizarNaArea(<Documentos />)
    await screen.findByText('Nenhum documento nesta situação.')

    const arquivo = new File(['%PDF-1.4'], 'nota.pdf', { type: 'application/pdf' })
    await userEvent.upload(screen.getByLabelText('Escolher documentos'), arquivo)

    expect(await screen.findByRole('heading', { name: 'nota.pdf' })).toBeInTheDocument()
    const envio = chamadas(fetchFalso, 'POST', '/api/restaurantes/10/documentos')[0]
    const corpo = envio.init?.body
    expect(corpo).toBeInstanceOf(FormData)
    expect((corpo as FormData).get('arquivo')).toBeInstanceOf(File)
    // Sem Content-Type manual: o navegador define o boundary do multipart.
    expect(new Headers(envio.init?.headers).has('Content-Type')).toBe(false)
    expect(screen.getByTitle('Visualização de nota.pdf')).toHaveAttribute(
      'src',
      '/api/restaurantes/10/documentos/1/arquivo',
    )
    expect(screen.getByText('11.222.333/0001-81')).toBeInTheDocument()
  })

  it('avisa quando o arquivo já foi enviado', async () => {
    simularBackend({
      'GET /api/restaurantes/10/documentos': () => json([]),
      'POST /api/restaurantes/10/documentos': () =>
        json({ detail: { mensagem: 'Este arquivo já foi enviado ("nota.pdf").', documento_id: 1 } }, 409),
    })
    renderizarNaArea(<Documentos />)
    await screen.findByText('Nenhum documento nesta situação.')

    await userEvent.upload(screen.getByLabelText('Escolher documentos'), new File(['%PDF'], 'copia.pdf'))

    expect(await screen.findByRole('alert')).toHaveTextContent('copia.pdf: Este arquivo já foi enviado ("nota.pdf").')
  })

  it('documento com erro pode ser lido novamente', async () => {
    const fetchFalso = simularBackend({
      'GET /api/restaurantes/10/documentos': () => json([documento({ status: 'erro' })]),
      'GET /api/restaurantes/10/documentos/1': () =>
        json(documento({ status: 'erro', erro: 'O OCR não está disponível.', dados_extraidos: null, texto_extraido: null })),
      'POST /api/restaurantes/10/documentos/1/reprocessar': () => json(documento()),
    })
    renderizarNaArea(<Documentos />)

    await userEvent.click(await screen.findByRole('button', { name: 'Abrir nota.pdf' }))
    expect(await screen.findByText('O OCR não está disponível.')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Ler novamente' }))

    await waitFor(() =>
      expect(chamadas(fetchFalso, 'POST', '/api/restaurantes/10/documentos/1/reprocessar')).toHaveLength(1),
    )
  })
})
