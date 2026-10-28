<#
.SYNOPSIS
  Sobe o sistema em MODO DE DEMONSTRAÇÃO, com dados fictícios, num banco separado.

.DESCRIPTION
  - Usa o banco restaurante_admin_demo (o de desenvolvimento não é tocado).
  - Guarda os documentos da demonstração em backend\armazenamento\demonstracao.
  - Na primeira vez (ou com -Recriar), apaga e recria os dados fictícios.
  - Abre o frontend em outra janela e roda o backend nesta. Ctrl+C encerra o backend.

.EXAMPLE
  .\iniciar_demonstracao.ps1 -Nome "Nome do Restaurante"
  .\iniciar_demonstracao.ps1 -Nome "Nome do Restaurante" -Recriar
#>
param(
    [string]$Nome = "Restaurante Demonstração",
    [switch]$Recriar
)

$ErrorActionPreference = "Stop"
$raiz = $PSScriptRoot
$backend = Join-Path $raiz "backend"

# Mesmo usuário e senha do banco de desenvolvimento, trocando só o nome do banco.
$linha = Select-String -Path (Join-Path $backend ".env") -Pattern '^DATABASE_URL=(.*)$'
if (-not $linha) { throw "DATABASE_URL não encontrada em backend\.env" }
$env:DATABASE_URL = $linha.Matches[0].Groups[1].Value -replace '/[^/]+$', '/restaurante_admin_demo'
$env:DOCUMENTOS_DIR = Join-Path $backend "armazenamento\demonstracao"
$env:MODO_DEMONSTRACAO = "true"

Push-Location $backend
try {
    Write-Host "Atualizando o banco de demonstração..." -ForegroundColor Cyan
    & .\.venv\Scripts\alembic upgrade head
    if ($LASTEXITCODE -ne 0) { throw "Falha nas migrações. O banco restaurante_admin_demo existe? (veja o README)" }

    $usuarios = & .\.venv\Scripts\python -c "from app.core.database import SessionLocal; from app.models import Usuario; s = SessionLocal(); print(s.query(Usuario).count())"
    if ($Recriar -or $usuarios -eq "0") {
        Write-Host "Criando os dados fictícios de '$Nome'..." -ForegroundColor Cyan
        & .\.venv\Scripts\python -m scripts.criar_demonstracao --nome $Nome
        if ($LASTEXITCODE -ne 0) { throw "Falha ao criar a demonstração." }
    } else {
        Write-Host "Usando a demonstração já existente (use -Recriar para começar do zero)." -ForegroundColor Cyan
    }

    Start-Process powershell -ArgumentList "-NoExit", "-Command", "npm.cmd --prefix '$raiz\frontend' run dev"
    Write-Host ""
    Write-Host "Abra http://127.0.0.1:5173  |  Login: demo@exemplo.com  |  Senha: demonstracao" -ForegroundColor Green
    Write-Host ""
    & .\.venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8000
}
finally {
    Pop-Location
}
