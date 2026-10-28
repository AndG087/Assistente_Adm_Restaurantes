# 006 — IA local: sugestão de categoria e assistente de dados

- **Data:** 2026-10-27
- **Status:** aceita

## Contexto

O enunciado pede sugestões de categoria e um chat que consulte os dados financeiros, com a regra de que **a IA nunca é fonte de verdade para valores**. O modelo local configurado é o `llama3.2:1b`.

Testes com o modelo real mostraram que ele é fraco para classificação: escolhendo a categoria de 11 descrições comuns, acertou 2 com o prompt simples e 5 com exemplos e raciocínio estruturado.

## Decisões

### Camadas determinísticas antes da IA

- **Sugestão de categoria:** (1) palavras-chave do vocabulário de restaurantes (`palavras_chave.py`), (2) categoria mais usada com o mesmo fornecedor, (3) IA. A resposta informa de onde veio a sugestão.
- **Assistente:** a pergunta é entendida primeiro por regras (`assistente/intencao.py` e `periodo.py`); a IA só classifica o que as regras não entendem e que pareça financeiro.

### A IA só escolhe dentro de listas fechadas

- Saída estruturada do Ollama (`format` com JSON Schema e `enum`) e temperatura 0.
- O backend confere de novo cada campo devolvido (categoria existente e ativa do restaurante; consulta e período entre os permitidos). Qualquer coisa fora da lista é descartada.
- O texto do usuário vai delimitado (`<<<...>>>`) e o prompt manda tratá-lo como dado. Isso reduz, mas não impede, manipulação; a garantia real é que o modelo não tem nenhuma ação disponível além de escolher numa lista.

### Números nunca passam pelo modelo

- As consultas do assistente rodam no banco, sempre com o `restaurante_id` do vínculo do usuário logado (nunca algo vindo da pergunta).
- As respostas são frases de modelos fixos preenchidas com os valores calculados. A IA não reescreve a resposta.
- Cada resposta informa o que foi consultado (ex.: "Total de despesas · 01/10/2026 a 31/10/2026") para o usuário perceber uma interpretação errada.
- Perguntas que não são sobre os dados vão para a conversa geral, identificada como "sem acesso aos dados do restaurante".

### Degradação sem Ollama

- Sugestão: sem IA, devolve "escolha manualmente" (não é erro).
- Assistente: perguntas entendidas pelas regras continuam respondidas; as que dependeriam da IA recebem uma orientação com exemplos; a conversa geral retorna 503.

## Consequências

- A cobertura das regras é limitada a frases comuns; perguntas fora delas dependem da qualidade do modelo.
- A conversa geral do modelo de 1B pode dar conselhos ruins (observado em teste). Recomenda-se um modelo maior (ex.: `llama3.2:3b`) quando houver memória.
- Ampliar as consultas do assistente exige adicionar a consulta em `intencao.CONSULTAS`, uma regra e um modelo de resposta em `consultas.py` — sempre determinístico.
