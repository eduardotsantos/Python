@echo off
:: ============================================================
:: Orion Gestao de P&D - Backup do Banco de Dados
:: Agendar no Agendador de Tarefas do Windows
:: ============================================================

:: --- CONFIGURACAO: ajuste os caminhos abaixo ---
set APP_DIR=C:\caminho\para\rd_project_management
set BACKUP_DIR=C:\backups\orion_pd
set MANTER_DIAS=30

:: --- Nao edite abaixo desta linha ---
set DB_FILE=%APP_DIR%\instance\rd_projects.db
set LOG_FILE=%BACKUP_DIR%\backup.log
set DATA=%DATE:~6,4%-%DATE:~3,2%-%DATE:~0,2%
set HORA=%TIME:~0,2%-%TIME:~3,2%-%TIME:~6,2%
set HORA=%HORA: =0%
set NOME_BACKUP=rd_projects_%DATA%_%HORA%.db

:: Criar diretorio de backup se nao existir
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

:: Registrar inicio no log
echo [%DATA% %TIME%] Iniciando backup... >> "%LOG_FILE%"

:: Verificar se o banco de dados existe
if not exist "%DB_FILE%" (
    echo [%DATA% %TIME%] ERRO: Banco de dados nao encontrado em %DB_FILE% >> "%LOG_FILE%"
    echo ERRO: Banco de dados nao encontrado em %DB_FILE%
    exit /b 1
)

:: Copiar o banco de dados
copy /Y "%DB_FILE%" "%BACKUP_DIR%\%NOME_BACKUP%" >nul 2>&1

if %ERRORLEVEL% == 0 (
    echo [%DATA% %TIME%] SUCESSO: Backup salvo em %BACKUP_DIR%\%NOME_BACKUP% >> "%LOG_FILE%"
    echo Backup criado com sucesso: %NOME_BACKUP%
) else (
    echo [%DATA% %TIME%] ERRO: Falha ao copiar banco de dados >> "%LOG_FILE%"
    echo ERRO: Falha ao criar backup
    exit /b 1
)

:: Remover backups mais antigos que MANTER_DIAS dias
forfiles /P "%BACKUP_DIR%" /M "rd_projects_*.db" /D -%MANTER_DIAS% /C "cmd /c del @path" >nul 2>&1
echo [%DATA% %TIME%] Limpeza: removidos backups com mais de %MANTER_DIAS% dias >> "%LOG_FILE%"

:: Mostrar espaco usado pelos backups
echo.
echo Backups armazenados em: %BACKUP_DIR%
dir /B "%BACKUP_DIR%\rd_projects_*.db" 2>nul | find /C ".db" > temp_count.txt
set /P TOTAL=<temp_count.txt
del temp_count.txt
echo Total de backups: %TOTAL%
echo [%DATA% %TIME%] Total de backups mantidos: %TOTAL% >> "%LOG_FILE%"
echo ---------------------------------------- >> "%LOG_FILE%"

exit /b 0
