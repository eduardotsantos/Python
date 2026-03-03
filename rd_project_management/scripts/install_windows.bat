@echo off
REM ============================================================
REM  Script de Instalacao - Sistema de Gestao de Projetos P&D
REM  Para Windows Server (AWS EC2)
REM ============================================================
REM  Execute como Administrador
REM ============================================================

setlocal EnableDelayedExpansion

echo.
echo ============================================================
echo   INSTALACAO DO SISTEMA DE GESTAO DE PROJETOS P^&D
echo ============================================================
echo.

REM Verificar se esta rodando como administrador
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERRO] Este script precisa ser executado como Administrador.
    echo Clique com botao direito e selecione "Executar como administrador"
    pause
    exit /b 1
)

REM Definir variaveis
set "INSTALL_DIR=C:\GestaoP&D"
set "PYTHON_VERSION=3.11.7"
set "PYTHON_URL=https://www.python.org/ftp/python/%PYTHON_VERSION%/python-%PYTHON_VERSION%-amd64.exe"
set "SERVICE_NAME=GestaoPD"
set "PORT=5000"

echo [1/7] Verificando Python...
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo Python nao encontrado. Baixando e instalando Python %PYTHON_VERSION%...

    REM Baixar Python
    powershell -Command "Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%TEMP%\python_installer.exe'"

    REM Instalar Python silenciosamente
    "%TEMP%\python_installer.exe" /quiet InstallAllUsers=1 PrependPath=1 Include_pip=1

    REM Atualizar PATH
    setx PATH "%PATH%;C:\Program Files\Python311;C:\Program Files\Python311\Scripts" /M

    echo Python instalado com sucesso!
) else (
    echo Python ja esta instalado.
)

echo.
echo [2/7] Criando diretorio de instalacao...
if not exist "%INSTALL_DIR%" (
    mkdir "%INSTALL_DIR%"
)
cd /d "%INSTALL_DIR%"

echo.
echo [3/7] Copiando arquivos da aplicacao...
REM Copiar arquivos (assumindo que estao no mesmo diretorio do script)
set "SCRIPT_DIR=%~dp0"
if exist "%SCRIPT_DIR%app.py" (
    xcopy "%SCRIPT_DIR%*" "%INSTALL_DIR%\" /E /Y /Q
    echo Arquivos copiados de %SCRIPT_DIR%
) else (
    echo [AVISO] Arquivos da aplicacao nao encontrados no diretorio do script.
    echo Copie manualmente os arquivos para %INSTALL_DIR%
)

echo.
echo [4/7] Criando ambiente virtual...
if not exist "%INSTALL_DIR%\venv" (
    python -m venv venv
)

echo.
echo [5/7] Instalando dependencias...
call "%INSTALL_DIR%\venv\Scripts\activate.bat"
pip install --upgrade pip
pip install -r requirements.txt
pip install waitress

echo.
echo [6/7] Configurando variaveis de ambiente...
REM Gerar chave secreta aleatoria
for /f "delims=" %%a in ('powershell -Command "[guid]::NewGuid().ToString()"') do set "SECRET_KEY=%%a"

REM Criar arquivo de configuracao
(
echo # Configuracao do Sistema Gestao P^&D
echo SECRET_KEY=%SECRET_KEY%
echo DATABASE_URL=sqlite:///%INSTALL_DIR:\=/%/rd_projects.db
echo PORT=%PORT%
echo FLASK_ENV=production
) > "%INSTALL_DIR%\.env"

echo.
echo [7/7] Criando servico Windows...

REM Criar script de inicializacao do servico
(
echo @echo off
echo cd /d "%INSTALL_DIR%"
echo call venv\Scripts\activate.bat
echo set FLASK_ENV=production
echo for /f "delims=" %%%%a in ^(.env^) do set %%%%a
echo python -m waitress --host=0.0.0.0 --port=%PORT% app:app
) > "%INSTALL_DIR%\start_service.bat"

REM Usar NSSM para criar servico Windows (se disponivel)
where nssm >nul 2>&1
if %errorLevel% equ 0 (
    nssm install %SERVICE_NAME% "%INSTALL_DIR%\start_service.bat"
    nssm set %SERVICE_NAME% AppDirectory "%INSTALL_DIR%"
    nssm set %SERVICE_NAME% Description "Sistema de Gestao de Projetos de P&D"
    nssm set %SERVICE_NAME% Start SERVICE_AUTO_START
    echo Servico Windows criado: %SERVICE_NAME%
) else (
    echo.
    echo [INFO] NSSM nao encontrado. Para instalar como servico Windows:
    echo   1. Baixe NSSM de https://nssm.cc/download
    echo   2. Extraia e copie nssm.exe para C:\Windows\System32
    echo   3. Execute: nssm install %SERVICE_NAME% "%INSTALL_DIR%\start_service.bat"
    echo.
    echo Alternativamente, execute manualmente: start_service.bat
)

echo.
echo ============================================================
echo   INSTALACAO CONCLUIDA!
echo ============================================================
echo.
echo Diretorio: %INSTALL_DIR%
echo Porta: %PORT%
echo.
echo Para iniciar manualmente:
echo   cd %INSTALL_DIR%
echo   start_service.bat
echo.
echo Acesse: http://localhost:%PORT%
echo Login padrao: admin / admin123
echo.
echo IMPORTANTE: Altere a senha do admin apos o primeiro acesso!
echo.
echo ============================================================

pause
