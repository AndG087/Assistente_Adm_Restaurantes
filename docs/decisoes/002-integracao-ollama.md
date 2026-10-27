# 002 — Integração com a IA local (Ollama)

- **Data:** 2026-10-27
- **Status:** aceita

## Contexto

A IA deve rodar localmente com Ollama, sem APIs externas, e o sistema precisa continuar funcionando quando o Ollama estiver desligado ou sem o modelo instalado.

## Decisão

- **Um único serviço** (`backend/app/services/ollama_service.py`) conversa com o Ollama. Rotas e demais módulos usam apenas esse serviço.
- Endpoints oficiais da API local: `GET /api/tags` (status e modelos instalados) e `POST /api/chat` com `stream: false`.
- Endereço, modelo e timeouts vêm de variáveis de ambiente. O modelo **nunca** é baixado automaticamente.
- **Status com cache curto** (10 s por padrão) e timeout próprio de 3 s, para não consultar o Ollama a cada requisição nem travar a interface. O cache é descartado quando o chat detecta que o Ollama caiu ou que o modelo sumiu.
- O chat **não** consulta o status antes de enviar a mensagem: chama `/api/chat` direto e traduz a falha (conexão recusada, timeout, 404 de modelo, resposta inválida) em exceções próprias. As rotas convertem essas exceções em respostas HTTP com mensagens fixas (503, 504 ou 502), sem expor detalhes internos.
- Nunca se devolve uma resposta "fingida": sem texto do modelo, a API responde com erro.
- **O navegador não conhece o Ollama.** O frontend chama apenas `/api/...`; em desenvolvimento, o Vite repassa essas chamadas ao backend (proxy), o que também dispensa configurar CORS.
- Um prompt de sistema fixo informa ao modelo que ele não tem acesso a dados do restaurante, não deve inventar valores e não executa ações.
- Os logs registram apenas o **tipo** de erro, nunca o conteúdo das mensagens.

## Consequências

- Cada mensagem é independente: o modelo não recebe o histórico da conversa. Enviar o histórico é uma evolução simples, a decidir na próxima etapa.
- A resposta só aparece quando o modelo termina de gerar (sem streaming). Em modelos pequenos isso é aceitável; streaming pode ser adicionado depois.
- O prompt de sistema **não é** uma barreira de segurança: modelos pequenos podem ignorá-lo. As garantias reais vêm do backend, que não dá ao modelo nenhuma ferramenta, acesso a dados ou capacidade de executar ações.
