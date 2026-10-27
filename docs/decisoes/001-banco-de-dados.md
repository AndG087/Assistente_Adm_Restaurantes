# 001 — Banco de dados: MySQL local com PyMySQL

- **Data:** 2026-10-27
- **Status:** aceita

## Contexto

O projeto deve rodar inteiramente no computador local, sem serviços pagos ou hospedados. O enunciado prefere MySQL e admite SQLite como alternativa temporária caso a instalação do MySQL fosse um obstáculo.

O MySQL Server 9.2 já estava instalado e em execução na máquina de desenvolvimento.

## Decisão

- Usar **MySQL 9.2 local** desde a primeira etapa, sem passar pelo SQLite.
- Banco `restaurante_admin`, com `utf8mb4` / `utf8mb4_unicode_ci` (acentuação e qualquer caractere Unicode).
- Usuário dedicado `restaurante_app@localhost`, com privilégios **somente** nesse banco. A aplicação nunca usa o `root`.
- Driver **PyMySQL** (Python puro, sem compilação no Windows) com o pacote **cryptography**, exigido para o método de autenticação `caching_sha2_password` — o único disponível no MySQL 9, que removeu o `mysql_native_password`.
- Acesso via **SQLAlchemy 2** e migrações via **Alembic**. A URL de conexão vem de `DATABASE_URL` no `backend/.env`; nenhuma senha fica no código ou no `alembic.ini`.

## Consequências

- Nenhuma tabela foi criada na etapa 1: o chat não persiste dados. As primeiras tabelas virão com os cadastros, já como migrações do Alembic.
- `GET /api/health` informa se o banco responde, mas o backend continua no ar se o MySQL estiver parado.
- Os testes automatizados não dependem do MySQL. Quando houver tabelas, será preciso decidir como testar a camada de dados (banco de teste MySQL separado é a opção mais fiel).
- Trocar de banco no futuro exige apenas mudar `DATABASE_URL` e o driver, desde que o código continue usando o SQLAlchemy.
