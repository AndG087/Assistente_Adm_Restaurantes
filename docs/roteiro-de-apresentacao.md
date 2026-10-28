# Roteiro de apresentação da demonstração

Objetivo: mostrar a ideia a quem administra um restaurante e **descobrir se faz sentido para a rotina dela** — não vender.
Duração sugerida: 15 minutos de demonstração e 15 de conversa. A conversa vale mais que a demonstração.

## Antes do encontro

- [ ] Rodar `.\iniciar_demonstracao.ps1 -Nome "Nome do Restaurante" -Recriar` no mesmo dia (as datas são relativas a hoje: os alertas mostram contas vencendo "hoje").
- [ ] Ollama aberto (o assistente funciona sem ele, mas a sugestão por IA e a conversa geral não).
- [ ] Testar o login: `demo@exemplo.com` / `demonstracao`.
- [ ] Deixar a janela do navegador em tela cheia e fechar outras abas.
- [ ] Levar papel para anotar as respostas dela.

## O que dizer logo no início

- "É um projeto meu, da faculdade, e queria sua opinião de quem vive isso todo dia."
- "**Os dados são inventados**, só para mostrar como funcionaria. Nenhum dado seu foi usado." (A faixa amarela no topo diz isso.)
- "Tudo roda no computador, sem mandar nada para a internet."

## Demonstração (ordem sugerida)

1. **Início** — "Ao abrir, você vê o que está vencido, o que vence hoje e o que vence na semana, e quanto já gastou no mês."
2. **Documentos** — o ponto alto.
   - Abrir a NF-e em PDF: o sistema leu valor, data, CNPJ e reconheceu o fornecedor. Clicar em **Sugerir** na categoria e **Criar despesa**.
   - Abrir a **foto da mesma nota**: aparece o aviso de possível duplicado. "Se alguém lançar a mesma nota duas vezes, o sistema avisa."
   - Abrir o boleto (foto): o sistema sugere "Conta a pagar" com o vencimento.
3. **Contas a pagar** — pagar uma conta vencida: "Ao marcar como paga, a despesa entra sozinha."
4. **Assistente** — usar as perguntas de exemplo e mais estas:
   - "Quanto gastei com bebidas este mês?"
   - "Quanto gastei com música ao vivo este mês?"
   - "Em que categorias gastei mais no mês passado?"
   - Mostrar que a resposta diz **o que foi consultado** e que os números vêm do sistema, não da IA.
5. **Relatórios** — gráfico dos últimos meses e **Exportar despesas (CSV)**, abrindo no Excel: "Isso poderia ir direto para o contador."

## Perguntas para ela (o objetivo do encontro)

Rotina e dor
- Hoje, como você controla as contas e as notas? (caderno, planilha, sistema, contador?)
- O que mais toma seu tempo ou mais dá dor de cabeça nessa parte?
- Já pagou conta atrasada ou em dobro por desorganização?

Encaixe
- Das telas que viu, qual usaria de verdade? Qual não faz falta?
- Quem lançaria as notas: você, um gerente, alguém do caixa?
- Você usa algum sistema de vendas (caixa/PDV) ou iFood? Gostaria de ver o faturamento junto com os gastos?
- O que o seu contador pede todo mês, e em que formato?

Confiança
- Você se sentiria confortável com os dados financeiros num programa assim? O que precisaria para confiar?
- Usaria no computador do restaurante, no seu, ou precisaria no celular?

Prioridade
- Se só uma coisa ficasse pronta primeiro, qual seria?

## O que NÃO prometer

- Não está pronto para uso real: falta backup, acesso pelo celular e outros cuidados de segurança antes de guardar dados verdadeiros.
- A leitura de fotos pode errar; por isso sempre há a conferência antes de lançar.
- O modelo de IA local é pequeno: a conversa geral não é confiável; as respostas sobre os dados, sim.
- Prazos e preço: o objetivo agora é ouvir.

## Depois do encontro

Anotar, no mesmo dia:

- As 3 maiores dores que ela citou, com as palavras dela.
- O que ela achou inútil.
- Quem usaria e onde (computador, celular).
- Se ela toparia testar com dados reais mais adiante (e em que condições).

Com isso, a próxima etapa é decidida pelas respostas — por exemplo, contas recorrentes, faturamento ou acesso pelo celular.
