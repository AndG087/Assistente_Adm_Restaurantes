# 005 — Documentos, OCR e conferência

- **Data:** 2026-10-27
- **Status:** aceita

## Contexto

Notas fiscais, boletos e comprovantes precisam virar despesas ou contas a pagar com o mínimo de digitação, sem enviar nada para serviços externos. O enunciado pede que a extração (OCR) seja separada da interpretação.

## Decisões

### Armazenamento

- Arquivos em `backend/armazenamento/documentos/{restaurante_id}/{uuid}.{ext}`, fora do Git. O nome enviado pelo usuário é só exibido, nunca usado como caminho; `armazenamento.caminho()` recusa qualquer caminho fora da pasta.
- Tipo decidido pelos primeiros bytes (PDF, JPEG, PNG), não pela extensão. Limite de 10 MB, lido sem carregar arquivos maiores na memória.
- O SHA-256 do conteúdo é único por restaurante: o mesmo arquivo não entra duas vezes.

### Extração (texto) separada da interpretação (campos)

- `extracao_texto.py`: PDF com texto embutido é lido pelo `pypdf`, sem OCR (mais rápido e exato). PDF escaneado é renderizado pelo `pypdfium2` (300 dpi) e, como fotos, passa pelo **Tesseract**, chamado como processo local com o idioma português. Imagens grandes demais são recusadas (proteção contra "bombas de descompressão") e a rotação EXIF de fotos de celular é corrigida.
- `interpretacao_documento.py`: **regras fixas** (expressões regulares) encontram valor total, datas de emissão e vencimento, CNPJ do emitente (ignorando o do próprio restaurante), número e chave de acesso da NF-e (cujo CNPJ e número são extraídos das posições oficiais da chave).
- Falha de leitura vira situação "erro" com mensagem; o documento pode ser lido de novo depois (ex.: após instalar o Tesseract).

### Conferência

- O usuário sempre revisa: o formulário vem preenchido, ele escolhe entre despesa e conta a pagar e confirma. Nada é lançado automaticamente.
- Fornecedor reconhecido pelo CNPJ; se não existir, pode ser cadastrado na própria tela.
- **Possíveis duplicados** são avisos, não bloqueios: mesma chave de NF-e em outro documento, mesmo número e fornecedor, ou mesmo valor em até 3 dias. A despesa gerada por uma conta paga não é listada junto com a conta (é a mesma operação).
- Documento conferido é mantido como comprovante (não pode ser excluído).

## Consequências

- O OCR é síncrono: o envio espera a leitura terminar (frações de segundo para PDFs com texto; alguns segundos por página escaneada). Lotes grandes pediriam uma fila em segundo plano.
- As regras de interpretação cobrem os formatos comuns (DANFE, boleto, cupom); layouts incomuns exigem correção manual na conferência.
- A interpretação por IA do texto do documento não foi implementada: com o modelo de 1B, os testes mostraram acertos baixos (decisão 006), e as regras fixas são previsíveis.
