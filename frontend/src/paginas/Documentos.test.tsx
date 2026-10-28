import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { chamadas, corpoEnviado, json, renderizarNaArea, simularBackend } from '../test/backendFalso'
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

// Rotas usadas pela tela de conferência (formulário e sugestões).
const CONFERENCIA = {
  'GET /api/restaurantes/10/documentos/*/conferencia': () =>
    json({ fornecedor_sugerido: null, possiveis_duplicados: [] }),
  'GET /api/restaurantes/10/categorias': () => json([{ id: 3, nome: 'Alimentos e insumos', ativo: true }]),
  'GET /api/restaurantes/10/fornecedores': () => json([{ id: 7, nome: 'Boa Comida', ativo: true }]),
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
      ...CONFERENCIA,
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
      ...CONFERENCIA,
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

  it('confere o documento e cria a despesa com o fornecedor reconhecido', async () => {
    const fetchFalso = simularBackend({
      ...CONFERENCIA,
      'GET /api/restaurantes/10/documentos/*/conferencia': () =>
        json({ fornecedor_sugerido: { id: 7, nome: 'Boa Comida' }, possiveis_duplicados: [] }),
      'GET /api/restaurantes/10/documentos': () => json([documento()]),
      'GET /api/restaurantes/10/documentos/1': () => json(documento()),
      'POST /api/restaurantes/10/documentos/1/confirmar': () => json(documento({ status: 'concluido', despesa_id: 5 })),
    })
    renderizarNaArea(<Documentos />)

    await userEvent.click(await screen.findByRole('button', { name: 'Abrir nota.pdf' }))
    expect(await screen.findByLabelText('Descrição')).toHaveValue('NF 4521 - Boa Comida')
    expect(screen.getByLabelText('Valor (R$)')).toHaveValue('1234,56')
    expect(screen.getByLabelText('Data da despesa')).toHaveValue('2026-10-05')
    await waitFor(() => expect(screen.getByLabelText('Fornecedor')).toHaveDisplayValue('Boa Comida'))
    await userEvent.selectOptions(screen.getByLabelText('Categoria'), 'Alimentos e insumos')
    await userEvent.click(screen.getByRole('button', { name: 'Criar despesa' }))

    await screen.findByRole('heading', { name: 'Documentos' })
    expect(corpoEnviado(chamadas(fetchFalso, 'POST', '/api/restaurantes/10/documentos/1/confirmar')[0])).toEqual({
      tipo: 'despesa',
      descricao: 'NF 4521 - Boa Comida',
      valor: '1234.56',
      data: '2026-10-05',
      categoria_id: 3,
      fornecedor_id: 7,
      numero_documento: '4521',
      observacoes: null,
    })
  })

  it('boleto vira conta a pagar e avisa sobre possível duplicado', async () => {
    const fetchFalso = simularBackend({
      ...CONFERENCIA,
      'GET /api/restaurantes/10/documentos/*/conferencia': () =>
        json({
          fornecedor_sugerido: null,
          possiveis_duplicados: [
            { tipo: 'conta', id: 4, descricao: 'Boleto do gás', valor: '380.00', data: '2026-10-25', motivo: 'Mesmo valor em data próxima' },
          ],
        }),
      'GET /api/restaurantes/10/documentos': () => json([documento()]),
      'GET /api/restaurantes/10/documentos/1': () =>
        json(documento({ dados_extraidos: { ...DADOS, valor: '380.00', data_vencimento: '2026-10-25', tipo_sugerido: 'conta', cnpj_emitente: null } })),
      'POST /api/restaurantes/10/documentos/1/confirmar': () => json(documento({ status: 'concluido', conta_pagar_id: 9 })),
    })
    renderizarNaArea(<Documentos />)

    await userEvent.click(await screen.findByRole('button', { name: 'Abrir nota.pdf' }))

    const aviso = await screen.findByText('Este documento pode já ter sido lançado:')
    expect(aviso.closest('[role="alert"]')).toHaveTextContent('Conta “Boleto do gás”')
    expect(screen.getByRole('button', { name: 'Conta a pagar' })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByLabelText('Vencimento')).toHaveValue('2026-10-25')
    await userEvent.click(screen.getByRole('button', { name: 'Criar conta a pagar' }))

    await waitFor(() =>
      expect(chamadas(fetchFalso, 'POST', '/api/restaurantes/10/documentos/1/confirmar')).toHaveLength(1),
    )
    expect(corpoEnviado(chamadas(fetchFalso, 'POST', '/api/restaurantes/10/documentos/1/confirmar')[0])).toMatchObject({
      tipo: 'conta',
      valor: '380.00',
      data: '2026-10-25',
    })
  })

  it('oferece cadastrar o fornecedor do CNPJ encontrado', async () => {
    const fetchFalso = simularBackend({
      ...CONFERENCIA,
      'GET /api/restaurantes/10/documentos': () => json([documento()]),
      'GET /api/restaurantes/10/documentos/1': () => json(documento()),
      'POST /api/restaurantes/10/fornecedores': () =>
        json({ id: 8, nome: 'Distribuidora Nova', documento: '11222333000181', ativo: true }, 201),
    })
    renderizarNaArea(<Documentos />)

    await userEvent.click(await screen.findByRole('button', { name: 'Abrir nota.pdf' }))
    await userEvent.type(await screen.findByLabelText('Nome do fornecedor'), 'Distribuidora Nova')
    await userEvent.click(screen.getByRole('button', { name: 'Cadastrar fornecedor' }))

    expect(await screen.findByLabelText('Descrição')).toHaveValue('NF 4521 - Distribuidora Nova')
    expect(corpoEnviado(chamadas(fetchFalso, 'POST', '/api/restaurantes/10/fornecedores')[0])).toMatchObject({
      nome: 'Distribuidora Nova',
      documento: '11222333000181',
    })
  })
})
