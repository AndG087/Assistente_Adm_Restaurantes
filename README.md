# Restaurante Admin AI

Assistente administrativo inteligente para pequenos e médios restaurantes. O objetivo é organizar notas fiscais, comprovantes, despesas, fornecedores e contas a pagar, com uma IA que ajuda a interpretar documentos e responder perguntas sobre os dados financeiros.

**Tudo roda no computador local**, com ferramentas gratuitas: nenhum serviço pago, API externa ou banco hospedado. A IA é executada pelo [Ollama](https://docs.ollama.com/).

> **Estado atual — etapa 5.** Já funciona:
>
> - contas de usuário (cadastro, login, logout) e restaurantes, com isolamento total entre restaurantes;
> - fornecedores e categorias financeiras (cada restaurante novo já vem com 14 categorias padrão);
> - despesas com filtros por período, categoria e texto, e totais por categoria calculados no banco;
> - contas a pagar com situação (vencida, vence hoje, a vencer, paga), pagamento que gera a despesa automaticamente e alertas de vencimento na página inicial;
> - chat com a IA local (exige login).
>
> A IA ainda **não** acessa dados financeiros, não cadastra nada e não executa ações. Próximos passos: importação de documentos com OCR e consultas da IA aos dados.

## Tecnologias

| Camada | Tecnologias |
|---|---|
| Frontend | React 19, TypeScript, Vite, CSS puro, Vitest + Testing Library |
| Backend | Python 3.12, FastAPI, Pydantic, SQLAlchemy 2, Alembic, httpx, Pytest |
| Banco de dados | MySQL 9.2 local (driver PyMySQL) |
| IA | Ollama local, modelo `llama3.2:1b` (configurável) |

## Pré-requisitos

- **Python 3.12** ou superior
- **Node.js 22** ou superior (com npm)
- **MySQL 8 ou 9** em execução local
- **Ollama** (opcional para iniciar o sistema; necessário para o chat)

## Estrutura

```
.
├── backend/
│   ├── app/
│   │   ├── api/          # rotas por recurso e dependências de acesso (deps.py)
│   │   ├── core/         # configurações, banco, senhas, tokens e data/hora
│   │   ├── models/       # tabelas (usuários, restaurantes, fornecedores, categorias, despesas, contas…)
│   │   ├── schemas/      # validação de entrada e saída (Pydantic) e validadores de CPF/CNPJ
│   │   ├── services/     # regras de negócio e integração com o Ollama
│   │   └── main.py       # aplicação FastAPI
│   ├── alembic/          # migrações do banco
│   ├── tests/            # testes do backend
│   ├── .env.example
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── paginas/      # Início, Despesas, Contas a pagar, Fornecedores, Categorias
│       ├── components/   # TelaAcesso, AreaLogada, FormLancamento, Cabecalho, chat…
│       ├── hooks/        # useSessao, useRestaurantes, useCarregar, useNavegacao…
│       ├── recursos/     # funções de acesso à API por recurso
│       ├── utils/        # formatação de dinheiro, datas e documentos
│       └── api.ts        # requisições ao backend e tratamento de erros
└── docs/decisoes/        # registro das decisões de arquitetura
```

## Instalação

Os comandos abaixo são para **PowerShell**, a partir da raiz do projeto.

### 1. Banco de dados (MySQL)

Entre no MySQL como root (o cliente `mysql` pode não estar no PATH):

```powershell
& "C:\Program Files\MySQL\MySQL Server 9.2\bin\mysql.exe" -u root -p
```

Crie o banco e um usuário exclusivo da aplicação:

```sql
CREATE DATABASE restaurante_admin CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE restaurante_admin_test CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'restaurante_app'@'localhost' IDENTIFIED BY 'escolha_uma_senha_forte';
GRANT ALL PRIVILEGES ON restaurante_admin.* TO 'restaurante_app'@'localhost';
GRANT ALL PRIVILEGES ON restaurante_admin_test.* TO 'restaurante_app'@'localhost';
EXIT;
```

O banco `restaurante_admin_test` é usado só pelos testes automatizados e é apagado a cada execução.

### 2. Backend (Python)

```powershell
python -m venv backend\.venv
backend\.venv\Scripts\python -m pip install -r backend\requirements.txt
Copy-Item backend\.env.example backend\.env
```

Edite `backend\.env` e coloque a senha do `restaurante_app` em `DATABASE_URL` e `TEST_DATABASE_URL`.

Crie as tabelas aplicando as migrações:

```powershell
cd backend
.venv\Scripts\alembic upgrade head
cd ..
```

Sempre que baixar uma versão nova do projeto, rode `alembic upgrade head` de novo. Para criar uma migração depois de alterar um modelo: `.venv\Scripts\alembic revision --autogenerate -m "descricao"` (revise o arquivo gerado antes de aplicar).

### 3. Frontend (Node)

```powershell
npm --prefix frontend install
```

### 4. Ollama e o modelo (etapa manual)

O sistema inicia sem o Ollama; só o chat depende dele. O modelo **nunca** é baixado automaticamente.

1. Instale o Ollama: <https://ollama.com/download>
2. Baixe o modelo (cerca de 1,3 GB):

   ```powershell
   ollama pull llama3.2:1b
   ```

3. Confirme que ele aparece na lista:

   ```powershell
   ollama list
   ```

Para usar outro modelo, baixe-o e altere `OLLAMA_MODEL` no `backend\.env`.

## Variáveis de ambiente

Ficam em `backend\.env` (que **não** vai para o Git). Modelo em [`backend/.env.example`](backend/.env.example).

| Variável | Padrão | Descrição |
|---|---|---|
| `DATABASE_URL` | — | Conexão com o MySQL (`mysql+pymysql://usuario:senha@localhost:3306/banco`) |
| `TEST_DATABASE_URL` | — | Banco dos testes; o nome precisa terminar em `_test` |
| `SESSAO_DURACAO_HORAS` | `12` | Validade do login |
| `COOKIE_SEGURO` | `false` | `true` apenas quando houver HTTPS |
| `OLLAMA_URL` | `http://localhost:11434` | Endereço da API local do Ollama |
| `OLLAMA_MODEL` | `llama3.2:1b` | Modelo usado no chat |
| `OLLAMA_TIMEOUT_SECONDS` | `120` | Tempo máximo para gerar uma resposta |
| `OLLAMA_STATUS_TIMEOUT_SECONDS` | `3` | Tempo máximo da checagem de status |
| `OLLAMA_STATUS_CACHE_SECONDS` | `10` | Cache do status do Ollama |

O frontend aceita opcionalmente `BACKEND_URL` (padrão `http://127.0.0.1:8000`) em `frontend\.env`, caso o backend rode em outra porta.

## Execução

Use dois terminais.

**Backend** (http://127.0.0.1:8000, documentação interativa em http://127.0.0.1:8000/docs):

```powershell
cd backend
.venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

**Frontend** (http://127.0.0.1:5173):

```powershell
npm --prefix frontend run dev
```

Abra http://127.0.0.1:5173, crie sua conta em **Criar conta** e cadastre o restaurante. O cabeçalho mostra o status do backend (e do banco) e da IA local.

A primeira mensagem do chat pode levar até um minuto: o Ollama carrega o modelo na memória. As seguintes são bem mais rápidas.

Ambos escutam apenas em `127.0.0.1`: não ficam acessíveis pela rede.

### Rotas da API

| Método | Rota | Login | Descrição |
|---|---|---|---|
| GET | `/api/health` | não | Backend no ar e situação do banco |
| GET | `/api/ia/status` | não | Ollama acessível e modelo instalado |
| POST | `/api/auth/registrar` | não | Cria a conta (`nome`, `email`, `senha`) e já inicia a sessão |
| POST | `/api/auth/login` | não | Inicia a sessão (`email`, `senha`) |
| POST | `/api/auth/logout` | — | Encerra a sessão |
| GET | `/api/auth/eu` | sim | Usuário logado |
| GET | `/api/restaurantes` | sim | Restaurantes dos quais o usuário é membro |
| POST | `/api/restaurantes` | sim | Cria um restaurante (`nome`, `cnpj` opcional); o usuário vira proprietário |
| GET | `/api/restaurantes/{id}` | sim | Um restaurante (404 se o usuário não for membro) |
| POST | `/api/ia/chat` | sim | Envia `{"mensagem": "..."}` e recebe `{"resposta": "...", "modelo": "..."}` |

A sessão é um cookie `HttpOnly` enviado automaticamente pelo navegador. Detalhes em [`docs/decisoes/003-autenticacao-e-isolamento.md`](docs/decisoes/003-autenticacao-e-isolamento.md).

As rotas financeiras ficam dentro do restaurante, `/api/restaurantes/{id}/...`, e todas exigem login e vínculo com o restaurante (sem vínculo, a resposta é 404):

| Método | Rota | Descrição |
|---|---|---|
| GET, POST | `.../fornecedores` | Lista (`busca`, `incluir_inativos`) e cria fornecedores |
| GET, PUT | `.../fornecedores/{id}` | Consulta e altera (inclusive `ativo`) |
| GET, POST | `.../categorias` | Lista (`incluir_inativas`) e cria categorias |
| PUT | `.../categorias/{id}` | Renomeia ou ativa/inativa |
| GET, POST | `.../despesas` | Lista (`de`, `ate`, `categoria_id`, `sem_categoria`, `fornecedor_id`, `busca`, `limite`, `deslocamento`) com `total` e `valor_total`; cria |
| GET | `.../despesas/resumo` | Totais por categoria no período (`de`, `ate`) |
| GET, PUT, DELETE | `.../despesas/{id}` | Consulta, altera e exclui |
| GET, POST | `.../contas-a-pagar` | Lista (`situacao` = `pendentes`, `vencidas`, `pagas` ou `todas`, mais filtros) e cria |
| GET | `.../contas-a-pagar/alertas` | Vencidas, que vencem hoje e nos próximos `dias` (padrão 7) |
| GET, PUT, DELETE | `.../contas-a-pagar/{id}` | Consulta, altera e exclui (só pendentes) |
| POST | `.../contas-a-pagar/{id}/pagar` | Marca como paga (`data_pagamento`, padrão hoje) e cria a despesa |
| POST | `.../contas-a-pagar/{id}/desfazer-pagamento` | Volta para pendente e remove a despesa gerada |

Valores em dinheiro são enviados e recebidos como texto com ponto decimal (`"1234.50"`), para não perder centavos.

## Testes

```powershell
# Backend (não precisa do MySQL nem do Ollama: tudo é simulado)
cd backend
.venv\Scripts\python -m pytest
cd ..

# Frontend
npm --prefix frontend test

# Checagem de tipos e build de produção do frontend
npm --prefix frontend run build
```

## Problemas comuns

| Sintoma | Causa provável e solução |
|---|---|
| Status "IA local: Ollama desligado" | O Ollama não está em execução. Abra o aplicativo Ollama ou rode `ollama serve`. |
| Status "Modelo llama3.2:1b não instalado" | Rode `ollama pull llama3.2:1b` e clique em **Verificar novamente**. |
| Chat responde "A IA demorou demais" | O modelo está carregando pela primeira vez ou a máquina está ocupada. Tente de novo ou aumente `OLLAMA_TIMEOUT_SECONDS`. |
| Status "Backend: Desconectado" | O backend não está rodando na porta 8000. Inicie-o (veja **Execução**). |
| Status "Conectado, banco indisponível" | O serviço do MySQL está parado ou a senha no `DATABASE_URL` está errada. Verifique o serviço `MySQL92` em *Serviços* do Windows. |
| `Access denied for user 'restaurante_app'` | A senha em `backend\.env` não confere com a do usuário no MySQL. |
| `RuntimeError: 'cryptography' package is required` | Instale as dependências pelo `requirements.txt`; o MySQL 9 exige esse pacote. |
| `npm create vite ... -- --template` ignora o template no PowerShell | O PowerShell descarta o `--`. Use `npm create vite@latest pasta '--' --template react-ts` ou rode pelo Git Bash. |
| Execução de scripts desabilitada ao rodar `npm` no PowerShell | Use `npm.cmd` no lugar de `npm`, ou ajuste a política com `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`. |

## Segurança

- Aplicação apenas local; nenhuma porta é publicada.
- Senhas apenas em `backend\.env`, fora do Git.
- Toda entrada é validada pelo backend (mensagem de 1 a 4000 caracteres, sem campos extras).
- Erros retornam mensagens fixas, sem detalhes internos; os logs não registram o conteúdo das mensagens.
- A IA não executa comandos, não acessa arquivos e não tem acesso a dados. Valores financeiros, quando existirem, virão do banco e de cálculos feitos pelo backend, nunca da IA.

Decisões de arquitetura: [`docs/decisoes/`](docs/decisoes/).
