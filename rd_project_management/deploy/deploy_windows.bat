@echo off
REM =============================================================================
REM DEPLOY PACKAGE - Orion P&D v2.0
REM Central de Conformidade + Orion Autonomos PMO
REM Windows Server
REM =============================================================================

echo ==================================================
echo   DEPLOY - Orion P&D v2.0
echo   Novos Modulos: Conformidade + PMO IA
echo ==================================================

REM Ajuste estes caminhos conforme seu servidor
set BASE_DIR=C:\inetpub\wwwroot\rd_project_management
set BACKUP_DIR=C:\backups\orion_pd_%date:~-4,4%%date:~-7,2%%date:~-10,2%_%time:~0,2%%time:~3,2%

echo.
echo [1/5] Criando backup...
mkdir "%BACKUP_DIR%" 2>nul
xcopy "%BASE_DIR%\app.py" "%BACKUP_DIR%\" /Y
xcopy "%BASE_DIR%\models.py" "%BACKUP_DIR%\" /Y
xcopy "%BASE_DIR%\templates" "%BACKUP_DIR%\templates\" /E /I /Y
xcopy "%BASE_DIR%\routes" "%BACKUP_DIR%\routes\" /E /I /Y
xcopy "%BASE_DIR%\static" "%BACKUP_DIR%\static\" /E /I /Y
echo       Backup criado em: %BACKUP_DIR%

echo.
echo [2/5] Criando diretorios necessarios...
mkdir "%BASE_DIR%\agents" 2>nul
mkdir "%BASE_DIR%\templates\compliance\risks" 2>nul
mkdir "%BASE_DIR%\templates\compliance\pending" 2>nul
mkdir "%BASE_DIR%\templates\compliance\nc" 2>nul
mkdir "%BASE_DIR%\templates\compliance\bugs" 2>nul
mkdir "%BASE_DIR%\templates\compliance\actions" 2>nul
mkdir "%BASE_DIR%\templates\pmo_agents" 2>nul
echo       Diretorios criados.

echo.
echo [3/5] Parando aplicacao...
echo       MANUAL: Pare o servico IIS ou o processo Python antes de continuar
echo       Pressione qualquer tecla quando estiver pronto...
pause >nul

echo.
echo [4/5] Aplicando migration...
cd /d "%BASE_DIR%"
python deploy\migrate_compliance_pmo.py
echo       Migration concluida.

echo.
echo [5/5] Reiniciando aplicacao...
echo       MANUAL: Reinicie o servico IIS ou inicie o processo Python
echo       Pressione qualquer tecla para finalizar...
pause >nul

echo.
echo ==================================================
echo   DEPLOY CONCLUIDO!
echo ==================================================
echo.
echo Novos recursos disponiveis:
echo   - /compliance - Central de Pendencias e Conformidade
echo   - /pmo - Orion Autonomos PMO (11 Agentes IA)
echo.
echo Em caso de problemas, restaure o backup:
echo   xcopy "%BACKUP_DIR%\*" "%BASE_DIR%\" /E /Y
echo.
pause
