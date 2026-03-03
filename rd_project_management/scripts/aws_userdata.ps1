<powershell>
# ============================================================
#  AWS EC2 User Data Script
#  Sistema de Gestao de Projetos P&D
#
#  Cole este script no campo "User Data" ao criar a instancia EC2
#  ou execute via Systems Manager (SSM)
# ============================================================

$ErrorActionPreference = "Continue"
$LogFile = "C:\install_log.txt"

function Log {
    param($msg)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$timestamp - $msg" | Out-File -FilePath $LogFile -Append
    Write-Host $msg
}

Log "Iniciando instalacao do Sistema Gestao P&D..."

# Variaveis
$InstallDir = "C:\GestaoPD"
$Port = 5000
$PythonVersion = "3.11.7"
$PythonUrl = "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-amd64.exe"
$AppUrl = "https://github.com/SEU_USUARIO/SEU_REPO/archive/refs/heads/main.zip"  # Altere para seu repositorio

# 1. Instalar Python
Log "Instalando Python $PythonVersion..."
$pythonInstaller = "$env:TEMP\python_installer.exe"
Invoke-WebRequest -Uri $PythonUrl -OutFile $pythonInstaller -UseBasicParsing
Start-Process -FilePath $pythonInstaller -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1 Include_pip=1" -Wait
Remove-Item $pythonInstaller -Force

# Atualizar PATH
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
Log "Python instalado"

# 2. Criar diretorio
Log "Criando diretorio de instalacao..."
New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
Set-Location $InstallDir

# 3. Baixar aplicacao (ajuste a URL para seu repositorio)
# Opcao A: Baixar do GitHub
# Log "Baixando aplicacao..."
# Invoke-WebRequest -Uri $AppUrl -OutFile "$env:TEMP\app.zip" -UseBasicParsing
# Expand-Archive -Path "$env:TEMP\app.zip" -DestinationPath $InstallDir -Force

# Opcao B: Clonar com Git (se Git estiver instalado)
# git clone https://github.com/SEU_USUARIO/SEU_REPO.git .

# Opcao C: Copiar de S3
# aws s3 cp s3://seu-bucket/gestao-pd/ . --recursive

# 4. Criar ambiente virtual
Log "Criando ambiente virtual..."
& "C:\Program Files\Python311\python.exe" -m venv venv

# 5. Instalar dependencias
Log "Instalando dependencias..."
& "$InstallDir\venv\Scripts\pip.exe" install --upgrade pip
& "$InstallDir\venv\Scripts\pip.exe" install flask flask-sqlalchemy flask-login flask-wtf werkzeug requests beautifulsoup4 apscheduler waitress

# 6. Configurar aplicacao
Log "Configurando aplicacao..."
$secretKey = [guid]::NewGuid().ToString()

$envContent = @"
SECRET_KEY=$secretKey
DATABASE_URL=sqlite:///$($InstallDir -replace '\\','/')/rd_projects.db
PORT=$Port
FLASK_ENV=production
"@
$envContent | Out-File -FilePath "$InstallDir\.env" -Encoding UTF8

# 7. Criar script de inicializacao
$startScript = @"
@echo off
cd /d $InstallDir
call venv\Scripts\activate.bat
python -m waitress --host=0.0.0.0 --port=$Port app:app
"@
$startScript | Out-File -FilePath "$InstallDir\start.bat" -Encoding ASCII

# 8. Configurar Firewall
Log "Configurando firewall..."
New-NetFirewallRule -DisplayName "GestaoPD-HTTP" -Direction Inbound -Protocol TCP -LocalPort $Port -Action Allow -ErrorAction SilentlyContinue

# 9. Criar tarefa agendada para iniciar na boot
Log "Configurando inicializacao automatica..."
$action = New-ScheduledTaskAction -Execute "$InstallDir\start.bat"
$trigger = New-ScheduledTaskTrigger -AtStartup
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
Register-ScheduledTask -TaskName "GestaoPD" -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force

# 10. Iniciar aplicacao
Log "Iniciando aplicacao..."
Start-ScheduledTask -TaskName "GestaoPD"

# 11. Aguardar e verificar
Start-Sleep -Seconds 10
try {
    $response = Invoke-WebRequest -Uri "http://localhost:$Port/login" -UseBasicParsing -TimeoutSec 5
    if ($response.StatusCode -eq 200) {
        Log "Aplicacao iniciada com sucesso!"
    }
} catch {
    Log "Aguardando aplicacao iniciar..."
}

# Obter IP publico
try {
    $publicIp = Invoke-RestMethod -Uri "http://169.254.169.254/latest/meta-data/public-ipv4" -TimeoutSec 2
    Log "Acesse: http://$publicIp`:$Port"
} catch {
    Log "IP publico nao disponivel"
}

Log "Instalacao concluida!"
Log "Login padrao: admin / admin123"
</powershell>
