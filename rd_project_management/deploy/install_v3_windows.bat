@echo off
setlocal enabledelayedexpansion
REM =============================================================================
REM INSTALADOR - Orion P&D v3.0 - WINDOWS SERVER
REM Novidades: Traducao completa (PT/EN/ES) + Esqueci Minha Senha (SMTP tenant)
REM =============================================================================
REM Uso:
REM   1. Extraia orion_pd_v3_deploy.zip (clique direito > Extrair tudo)
REM   2. Abra o Prompt de Comando COMO ADMINISTRADOR
REM   3. cd para a pasta extraida
REM   4. install_v3_windows.bat
REM      ou: install_v3_windows.bat "D:\outro\caminho\da\app"
REM =============================================================================

REM Caminho da aplicacao no servidor (ajuste se necessario ou passe como parametro)
set "BASE_DIR=C:\apps\rd_project_managementv45"
if not "%~1"=="" set "BASE_DIR=%~1"

set "BACKUP_DIR=C:\backups\orion_v3_%date:~-4,4%%date:~-7,2%%date:~-10,2%_%time:~0,2%%time:~3,2%"
set "BACKUP_DIR=%BACKUP_DIR: =0%"
set "PKG_DIR=%~dp0"

echo ==================================================================
echo   INSTALADOR - Orion P&D v3.0 (Windows Server)
echo   Traducao completa EN/ES + Reset de Senha via SMTP do tenant
echo ==================================================================
echo.
echo   Diretorio de instalacao : %BASE_DIR%
echo   Diretorio do pacote     : %PKG_DIR%
echo   Backup sera criado em   : %BACKUP_DIR%
echo.

if not exist "%BASE_DIR%\app.py" (
    echo [ERRO] Nao encontrei app.py em %BASE_DIR%
    echo        Informe o caminho correto:
    echo        install_v3_windows.bat "C:\caminho\da\aplicacao"
    pause
    exit /b 1
)

set /p CONFIRM="Continuar com a instalacao? (S/N) "
if /i not "%CONFIRM%"=="S" (
    echo Instalacao cancelada.
    exit /b 0
)

REM -----------------------------------------------------------------------------
REM 1. BACKUP
REM -----------------------------------------------------------------------------
echo.
echo [1/7] Criando backup...
mkdir "%BACKUP_DIR%" 2>nul
xcopy "%BASE_DIR%\app.py" "%BACKUP_DIR%\" /Y >nul
xcopy "%BASE_DIR%\models.py" "%BACKUP_DIR%\" /Y >nul
if exist "%BASE_DIR%\extensions.py" xcopy "%BASE_DIR%\extensions.py" "%BACKUP_DIR%\" /Y >nul
if exist "%BASE_DIR%\babel.cfg" xcopy "%BASE_DIR%\babel.cfg" "%BACKUP_DIR%\" /Y >nul
xcopy "%BASE_DIR%\requirements.txt" "%BACKUP_DIR%\" /Y >nul 2>nul
xcopy "%BASE_DIR%\routes" "%BACKUP_DIR%\routes\" /E /I /Y >nul
xcopy "%BASE_DIR%\services" "%BACKUP_DIR%\services\" /E /I /Y >nul
xcopy "%BASE_DIR%\templates" "%BACKUP_DIR%\templates\" /E /I /Y >nul
if exist "%BASE_DIR%\translations" xcopy "%BASE_DIR%\translations" "%BACKUP_DIR%\translations\" /E /I /Y >nul
REM Backup dos bancos SQLite
xcopy "%BASE_DIR%\*.db" "%BACKUP_DIR%\" /Y >nul 2>nul
if exist "%BASE_DIR%\instance" xcopy "%BASE_DIR%\instance\*.db" "%BACKUP_DIR%\" /Y >nul 2>nul
echo       Backup criado em: %BACKUP_DIR%

REM -----------------------------------------------------------------------------
REM 2. PARAR APLICACAO
REM -----------------------------------------------------------------------------
echo.
echo [2/7] Parando aplicacao...
set "STOPPED="

REM Tenta servico Windows
sc query OrionPD >nul 2>&1
if not errorlevel 1 (
    net stop OrionPD >nul 2>&1
    set "STOPPED=servico"
    echo       Servico OrionPD parado.
)

REM Tenta IIS Application Pool
if "%STOPPED%"=="" (
    %windir%\system32\inetsrv\appcmd list apppool "OrionPD" >nul 2>&1
    if not errorlevel 1 (
        %windir%\system32\inetsrv\appcmd stop apppool /apppool.name:"OrionPD" >nul 2>&1
        set "STOPPED=iis"
        echo       Application Pool OrionPD parado no IIS.
    )
)

if "%STOPPED%"=="" (
    echo       [MANUAL] Nao detectei servico OrionPD nem App Pool no IIS.
    echo                Se a aplicacao estiver rodando (python/waitress),
    echo                PARE-A AGORA em outra janela.
    echo.
    pause
)

REM -----------------------------------------------------------------------------
REM 3. COPIAR ARQUIVOS
REM -----------------------------------------------------------------------------
echo.
echo [3/7] Copiando arquivos...

xcopy "%PKG_DIR%app.py" "%BASE_DIR%\" /Y >nul && echo       core: app.py
xcopy "%PKG_DIR%models.py" "%BASE_DIR%\" /Y >nul && echo       core: models.py
xcopy "%PKG_DIR%extensions.py" "%BASE_DIR%\" /Y >nul && echo       core: extensions.py
xcopy "%PKG_DIR%babel.cfg" "%BASE_DIR%\" /Y >nul && echo       core: babel.cfg
xcopy "%PKG_DIR%requirements.txt" "%BASE_DIR%\" /Y >nul && echo       core: requirements.txt

xcopy "%PKG_DIR%routes\*.py" "%BASE_DIR%\routes\" /Y >nul && echo       routes\ atualizado
xcopy "%PKG_DIR%services\*.py" "%BASE_DIR%\services\" /Y >nul && echo       services\ atualizado (inclui email_service.py NOVO)
xcopy "%PKG_DIR%templates" "%BASE_DIR%\templates\" /E /I /Y >nul && echo       templates\ atualizado (77 arquivos com i18n)
xcopy "%PKG_DIR%translations" "%BASE_DIR%\translations\" /E /I /Y >nul && echo       translations\ atualizado (pt_BR, en, es + .mo compilados)

mkdir "%BASE_DIR%\deploy" 2>nul
xcopy "%PKG_DIR%migrate_password_reset.py" "%BASE_DIR%\deploy\" /Y >nul && echo       deploy\migrate_password_reset.py copiado

REM -----------------------------------------------------------------------------
REM 4. DEPENDENCIAS
REM -----------------------------------------------------------------------------
echo.
echo [4/7] Instalando dependencias novas (Flask-Babel, Flask-Mail, Babel)...

set "PIP=pip"
if exist "%BASE_DIR%\venv\Scripts\pip.exe" (
    set "PIP=%BASE_DIR%\venv\Scripts\pip.exe"
    echo       Usando virtualenv: %BASE_DIR%\venv
)
%PIP% install -q Flask-Babel==4.0.0 Flask-Mail==0.9.1 Babel==2.14.0
if errorlevel 1 (
    echo       [AVISO] Falha ao instalar via pip. Instale manualmente:
    echo               %PIP% install Flask-Babel Flask-Mail Babel
) else (
    echo       Dependencias OK.
)

REM -----------------------------------------------------------------------------
REM 5. MIGRACAO DO BANCO
REM -----------------------------------------------------------------------------
echo.
echo [5/7] Aplicando migracao do banco (colunas de reset de senha)...

set "PYTHON=python"
if exist "%BASE_DIR%\venv\Scripts\python.exe" set "PYTHON=%BASE_DIR%\venv\Scripts\python.exe"

cd /d "%BASE_DIR%"
%PYTHON% deploy\migrate_password_reset.py
echo       (Obs: o app.py tambem cria as colunas sozinho no primeiro start)

REM -----------------------------------------------------------------------------
REM 6. VALIDACAO
REM -----------------------------------------------------------------------------
echo.
echo [6/7] Validando instalacao...
set ERRORS=0

for %%F in (
    "services\email_service.py"
    "templates\auth\forgot_password.html"
    "templates\auth\reset_password.html"
    "translations\en\LC_MESSAGES\messages.mo"
    "translations\es\LC_MESSAGES\messages.mo"
    "translations\pt_BR\LC_MESSAGES\messages.mo"
) do (
    if exist "%BASE_DIR%\%%~F" (
        echo       OK: %%~F
    ) else (
        echo       FALTANDO: %%~F
        set /a ERRORS+=1
    )
)

if %ERRORS% gtr 0 (
    echo.
    echo       [ERRO] %ERRORS% arquivo(s) faltando. Verifique o pacote.
    pause
    exit /b 1
)

REM -----------------------------------------------------------------------------
REM 7. REINICIAR APLICACAO
REM -----------------------------------------------------------------------------
echo.
echo [7/7] Reiniciando aplicacao...
if "%STOPPED%"=="servico" (
    net start OrionPD >nul 2>&1
    echo       Servico OrionPD reiniciado.
) else if "%STOPPED%"=="iis" (
    %windir%\system32\inetsrv\appcmd start apppool /apppool.name:"OrionPD" >nul 2>&1
    echo       Application Pool OrionPD reiniciado no IIS.
) else (
    echo       [MANUAL] Inicie a aplicacao:
    echo                cd %BASE_DIR%
    echo                waitress-serve --port=5000 --call app:create_app
    echo                ou: python app.py
)

echo.
echo ==================================================================
echo   INSTALACAO CONCLUIDA!
echo ==================================================================
echo.
echo   Novidades desta versao:
echo    - Traducao completa de TODAS as telas (PT/EN/ES)
echo    - Seletor de idioma no menu e no cadastro de usuario
echo    - "Esqueci minha senha" na tela de login
echo      (email enviado via SMTP configurado na empresa/tenant)
echo.
echo   Verifique:
echo    1. http://localhost:5000/login - link "Esqueci minha senha"
echo    2. Troque o idioma no menu e navegue pelas telas
echo    3. Configure o SMTP do tenant em:
echo       Empresas ^> Editar ^> Configuracao de Email
echo.
echo   Rollback em caso de problemas:
echo    xcopy "%BACKUP_DIR%\*" "%BASE_DIR%\" /E /Y
echo.
pause
