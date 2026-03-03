# ============================================================
#  Script de Instalacao PowerShell
#  Sistema de Gestao de Projetos P&D
#  Para Windows Server (AWS EC2)
# ============================================================
#  Execute como Administrador:
#  Set-ExecutionPolicy Bypass -Scope Process -Force
#  .\install_windows.ps1
# ============================================================

param(
    [string]$InstallDir = "C:\GestaoPD",
    [int]$Port = 5000,
    [string]$ServiceName = "GestaoPD",
    [switch]$SkipPython,
    [switch]$SkipService
)

$ErrorActionPreference = "Stop"

# Cores para output
function Write-Status { param($msg) Write-Host "[*] $msg" -ForegroundColor Cyan }
function Write-Success { param($msg) Write-Host "[+] $msg" -ForegroundColor Green }
function Write-Error { param($msg) Write-Host "[!] $msg" -ForegroundColor Red }
function Write-Warning { param($msg) Write-Host "[!] $msg" -ForegroundColor Yellow }

Write-Host ""
Write-Host "============================================================" -ForegroundColor Blue
Write-Host "   INSTALACAO DO SISTEMA DE GESTAO DE PROJETOS P&D" -ForegroundColor Blue
Write-Host "============================================================" -ForegroundColor Blue
Write-Host ""

# Verificar se esta rodando como administrador
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Error "Este script precisa ser executado como Administrador."
    Write-Host "Execute: Start-Process PowerShell -Verb RunAs -ArgumentList '-File', '$PSCommandPath'"
    exit 1
}

# 1. Verificar/Instalar Python
Write-Status "Passo 1/8: Verificando Python..."
$pythonInstalled = $false
try {
    $pythonVersion = python --version 2>&1
    if ($pythonVersion -match "Python 3") {
        Write-Success "Python encontrado: $pythonVersion"
        $pythonInstalled = $true
    }
} catch {}

if (-not $pythonInstalled -and -not $SkipPython) {
    Write-Status "Instalando Python via winget..."
    try {
        winget install Python.Python.3.11 --silent --accept-package-agreements --accept-source-agreements
        # Atualizar PATH
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        Write-Success "Python instalado com sucesso!"
    } catch {
        Write-Warning "Nao foi possivel instalar Python automaticamente."
        Write-Host "Baixe manualmente de: https://www.python.org/downloads/"
        exit 1
    }
}

# 2. Criar diretorio de instalacao
Write-Status "Passo 2/8: Criando diretorio de instalacao..."
if (-not (Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
}
Write-Success "Diretorio: $InstallDir"

# 3. Copiar arquivos
Write-Status "Passo 3/8: Copiando arquivos da aplicacao..."
$scriptDir = Split-Path -Parent $PSCommandPath
$sourceDir = Split-Path -Parent $scriptDir

if (Test-Path "$sourceDir\app.py") {
    Copy-Item -Path "$sourceDir\*" -Destination $InstallDir -Recurse -Force -Exclude @("venv", "__pycache__", "*.db", ".git", "scripts")
    Write-Success "Arquivos copiados de: $sourceDir"
} else {
    Write-Warning "Arquivos da aplicacao nao encontrados em $sourceDir"
    Write-Host "Copie manualmente os arquivos para $InstallDir"
}

Set-Location $InstallDir

# 4. Criar ambiente virtual
Write-Status "Passo 4/8: Criando ambiente virtual..."
if (-not (Test-Path "$InstallDir\venv")) {
    python -m venv venv
}
Write-Success "Ambiente virtual criado"

# 5. Ativar venv e instalar dependencias
Write-Status "Passo 5/8: Instalando dependencias..."
& "$InstallDir\venv\Scripts\Activate.ps1"
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
pip install waitress --quiet
Write-Success "Dependencias instaladas"

# 6. Configurar variaveis de ambiente
Write-Status "Passo 6/8: Configurando aplicacao..."
$secretKey = [guid]::NewGuid().ToString()

$envContent = @"
# Configuracao do Sistema Gestao P&D
# Gerado automaticamente em $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
SECRET_KEY=$secretKey
DATABASE_URL=sqlite:///$($InstallDir -replace '\\','/')/rd_projects.db
PORT=$Port
FLASK_ENV=production
"@

$envContent | Out-File -FilePath "$InstallDir\.env" -Encoding UTF8
Write-Success "Arquivo .env criado"

# 7. Criar script de inicializacao
Write-Status "Passo 7/8: Criando scripts de inicializacao..."

# Script PowerShell para iniciar
$startScript = @"
# Script de Inicializacao - Gestao P&D
Set-Location "$InstallDir"
& "$InstallDir\venv\Scripts\Activate.ps1"

# Carregar variaveis do .env
Get-Content "$InstallDir\.env" | ForEach-Object {
    if (`$_ -match "^([^#=]+)=(.*)$") {
        [Environment]::SetEnvironmentVariable(`$matches[1], `$matches[2], "Process")
    }
}

Write-Host "Iniciando Gestao P&D na porta $Port..."
Write-Host "Acesse: http://localhost:$Port"
python -m waitress --host=0.0.0.0 --port=$Port app:app
"@
$startScript | Out-File -FilePath "$InstallDir\start.ps1" -Encoding UTF8

# Script BAT para iniciar
$startBat = @"
@echo off
cd /d "$InstallDir"
call venv\Scripts\activate.bat
echo Iniciando Gestao P&D na porta $Port...
echo Acesse: http://localhost:$Port
python -m waitress --host=0.0.0.0 --port=$Port app:app
"@
$startBat | Out-File -FilePath "$InstallDir\start.bat" -Encoding ASCII

Write-Success "Scripts de inicializacao criados"

# 8. Configurar Firewall
Write-Status "Passo 8/8: Configurando firewall..."
try {
    $ruleName = "GestaoPD-HTTP-$Port"
    $existingRule = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
    if (-not $existingRule) {
        New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Protocol TCP -LocalPort $Port -Action Allow | Out-Null
        Write-Success "Regra de firewall criada para porta $Port"
    } else {
        Write-Success "Regra de firewall ja existe"
    }
} catch {
    Write-Warning "Nao foi possivel configurar firewall automaticamente"
    Write-Host "Configure manualmente: Permitir TCP na porta $Port"
}

# Criar servico Windows (opcional)
if (-not $SkipService) {
    Write-Status "Configurando servico Windows..."

    # Verificar se NSSM esta disponivel
    $nssmPath = Get-Command nssm -ErrorAction SilentlyContinue
    if ($nssmPath) {
        # Remover servico existente
        & nssm stop $ServiceName 2>$null
        & nssm remove $ServiceName confirm 2>$null

        # Instalar novo servico
        & nssm install $ServiceName "$InstallDir\venv\Scripts\python.exe" "-m waitress --host=0.0.0.0 --port=$Port app:app"
        & nssm set $ServiceName AppDirectory $InstallDir
        & nssm set $ServiceName Description "Sistema de Gestao de Projetos de P&D"
        & nssm set $ServiceName Start SERVICE_AUTO_START
        & nssm set $ServiceName AppStdout "$InstallDir\logs\stdout.log"
        & nssm set $ServiceName AppStderr "$InstallDir\logs\stderr.log"

        # Criar diretorio de logs
        New-Item -ItemType Directory -Path "$InstallDir\logs" -Force | Out-Null

        Write-Success "Servico Windows '$ServiceName' criado"
        Write-Host "Para iniciar o servico: nssm start $ServiceName" -ForegroundColor Yellow
    } else {
        Write-Warning "NSSM nao encontrado. Servico Windows nao foi criado."
        Write-Host ""
        Write-Host "Para instalar NSSM:" -ForegroundColor Yellow
        Write-Host "  1. Baixe de: https://nssm.cc/download"
        Write-Host "  2. Extraia e copie nssm.exe para C:\Windows\System32"
        Write-Host "  3. Execute novamente este script"
        Write-Host ""
        Write-Host "Ou use o Agendador de Tarefas para executar start.bat na inicializacao"
    }
}

# Inicializar banco de dados
Write-Status "Inicializando banco de dados..."
& "$InstallDir\venv\Scripts\python.exe" -c "from app import create_app; create_app()"
Write-Success "Banco de dados inicializado"

# Resumo final
Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "   INSTALACAO CONCLUIDA COM SUCESSO!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Diretorio de Instalacao: $InstallDir" -ForegroundColor White
Write-Host "Porta: $Port" -ForegroundColor White
Write-Host ""
Write-Host "Para iniciar manualmente:" -ForegroundColor Yellow
Write-Host "  .\start.ps1" -ForegroundColor White
Write-Host "  ou" -ForegroundColor Yellow
Write-Host "  .\start.bat" -ForegroundColor White
Write-Host ""
Write-Host "Acesse: http://localhost:$Port" -ForegroundColor Cyan
Write-Host "Ou externamente: http://<IP-DO-SERVIDOR>:$Port" -ForegroundColor Cyan
Write-Host ""
Write-Host "Login padrao:" -ForegroundColor Yellow
Write-Host "  Usuario: admin" -ForegroundColor White
Write-Host "  Senha:   admin123" -ForegroundColor White
Write-Host ""
Write-Host "IMPORTANTE: Altere a senha do admin apos o primeiro acesso!" -ForegroundColor Red
Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
