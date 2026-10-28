# 004 — Modelo financeiro: cadastros, despesas e contas a pagar

- **Data:** 2026-10-27
- **Status:** aceita

## Contexto

As etapas 3 a 5 introduzem os primeiros dados financeiros: fornecedores, categorias, despesas e contas a pagar. O enunciado exige que valores financeiros venham do banco, com cálculos determinísticos no backend, e que cada restaurante só veja os próprios dados.

## Decisões

### Dinheiro

- Coluna `DECIMAL(12,2)` no MySQL e `Decimal` no Python: valores exatos (com `float`, 0,10 + 0,20 = 0,30000000000000004).
- Totais e somas por categoria são feitos pelo banco (`SUM`) e devolvidos prontos; o frontend apenas exibe.
- Na API, valores trafegam como **texto** (`"1234.50"`) para nenhum cliente convertê-los em `float` sem perceber.
- Entrada: maior que zero, no máximo 2 casas decimais e 10 dígitos inteiros.

### Isolamento

- Toda tabela financeira tem `restaurante_id`, e toda consulta dos serviços filtra por ele.
- As rotas ficam em `/api/restaurantes/{id}/...` e usam a dependência `VinculoRestaurante` (decisão 003).
- Ao receber `categoria_id` ou `fornecedor_id`, o backend confere se pertencem ao **mesmo** restaurante (`services/referencias.py`). Sem isso, um usuário poderia associar à sua despesa o id de um fornecedor alheio e ler o nome dele.

### Cadastros

- Fornecedores e categorias **não são apagados**, e sim inativados: podem estar em despesas antigas (as chaves estrangeiras usam `RESTRICT`).
- Inativos não podem ser escolhidos em lançamentos novos, mas continuam valendo nos lançamentos que já os usavam.
- CPF/CNPJ do fornecedor é único por restaurante; nomes de categoria também (ignorando maiúsculas e acentos, pela collation do banco).
- Cada restaurante novo recebe 14 categorias padrão; a migração da etapa 3 também as criou para os restaurantes já existentes.

### Contas a pagar × despesas

- **Despesa** é o gasto realizado (entra nos totais do período pela sua data). **Conta a pagar** é uma obrigação com vencimento.
- Ao **pagar** uma conta, o backend cria a despesa correspondente na mesma transação, com a data do pagamento (regime de caixa). Assim o usuário não lança a mesma coisa duas vezes.
- A despesa gerada guarda `conta_pagar_id` (único) e só muda pela conta: para corrigi-la, desfaz-se o pagamento, o que remove a despesa e devolve a conta a pendente.
- Conta paga não pode ser editada nem excluída; a data de pagamento não pode ser futura.
- A situação (`vencida`, `vence_hoje`, `a_vencer`, `paga`) é **calculada** a partir das datas, nunca armazenada, para não ficar desatualizada.
- "Hoje" é a data do computador (`core/tempo.py`): a aplicação roda localmente, no fuso do restaurante.

### Migrações

- Cada etapa tem a sua migração, revisada antes de aplicar e testada nos dois sentidos.
- No MySQL, um índice usado por chave estrangeira não pode ser removido antes dela (erro 1553). Por isso os `downgrade` apagam tabelas inteiras em vez de índices um a um, e restrições criadas depois têm nomes explícitos.

## Consequências

- Ainda não há contas recorrentes (aluguel todo mês) nem parcelamento: cada conta é cadastrada individualmente.
- Não há pagamento parcial nem juros/multa: o valor pago é o valor da conta. Se necessário, edita-se a conta antes de pagar.
- A busca textual usa `LIKE '%texto%'`, suficiente para o volume de um restaurante; volumes grandes pediriam índice de texto completo.
