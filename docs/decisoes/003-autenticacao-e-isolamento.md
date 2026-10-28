# 003 — Autenticação por sessão e isolamento por restaurante

- **Data:** 2026-10-27
- **Status:** aceita

## Contexto

O produto atenderá vários restaurantes, e cada usuário só pode ver os dados dos restaurantes aos quais pertence. Isso precisa existir **antes** de qualquer dado financeiro entrar no sistema.

## Decisão

### Sessões no servidor + cookie HttpOnly (e não JWT no `localStorage`)

- No login, o backend gera um token aleatório (`secrets.token_urlsafe(32)`), grava **apenas o hash SHA-256** dele na tabela `sessoes` e envia o token puro num cookie `HttpOnly`, `SameSite=Lax`, restrito ao caminho `/api`.
- `HttpOnly` impede que JavaScript da página leia o token, o que reduz o estrago de um eventual XSS. `SameSite=Lax` impede que outros sites façam POSTs autenticados.
- Logout apaga a sessão no banco: o token deixa de valer na hora, o que um JWT não permite sem uma lista de bloqueio.
- A sessão expira em 12 h (`SESSAO_DURACAO_HORAS`). Usuário desativado perde o acesso imediatamente, inclusive nas sessões abertas.

### Senhas com scrypt da biblioteca padrão

- `hashlib.scrypt` (N=2^14, r=8, p=1, sal aleatório de 16 bytes), comparação com `hmac.compare_digest`. Os parâmetros ficam gravados no próprio hash, permitindo aumentá-los no futuro.
- Evita uma dependência nova. Se houver necessidade, migrar para Argon2 (pacote `pwdlib`) é possível verificando o prefixo do hash.
- Login responde a mesma mensagem para e-mail inexistente e senha errada, e gasta o mesmo tempo nos dois casos.

### Isolamento por vínculo

- A tabela `membros_restaurante` liga usuário e restaurante, com um papel (`proprietario` ou `membro`). Quem cria um restaurante vira proprietário.
- **Toda rota de dados de um restaurante deve usar a dependência `VinculoRestaurante`** (`backend/app/api/deps.py`), que lê o `restaurante_id` da URL e responde **404** se o usuário não for membro. 404 (e não 403) para não revelar que o restaurante existe.
- Os dados financeiros futuros terão `restaurante_id` e serão sempre filtrados por ele nos serviços.

### Testes com MySQL real

- Os testes usam o banco `restaurante_admin_test` (`TEST_DATABASE_URL`), recriado a cada execução. Uma trava recusa qualquer banco cujo nome não termine em `_test`.

## Consequências

- O chat passou a exigir login; `/api/health` e `/api/ia/status` seguem públicos para a tela de entrada mostrar o status.
- O cadastro é aberto (qualquer pessoa com acesso à máquina cria conta). Aceitável enquanto o sistema roda só localmente; antes de expor na rede será preciso convite ou aprovação.
- Ainda não há limite de tentativas de login.
- Equipe (complemento, 2026-10-27): o proprietário adiciona pessoas que já têm conta, pelo e-mail; membros usam as funções financeiras, só proprietários gerenciam a equipe, e o último proprietário não pode ser removido nem rebaixado. Gerenciar a equipe responde 403 a um membro (ele já sabe que o restaurante existe).
- Em produção com HTTPS, `COOKIE_SEGURO` deve ser `true`.
