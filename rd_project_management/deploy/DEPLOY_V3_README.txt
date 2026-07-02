================================================================================
                    PACOTE DE DEPLOY - ORION P&D v3.0
        Traducao Completa (PT/EN/ES) + Esqueci Minha Senha (SMTP Tenant)
================================================================================

NOVIDADES DESTA VERSAO
----------------------
1. TRADUCAO COMPLETA DO SISTEMA
   - Todas as telas, status, relatorios e PDFs traduzem para EN e ES
   - 1.100+ strings traduzidas nos 3 idiomas
   - Seletor de idioma com bandeiras no menu superior
   - Campo de idioma no cadastro/edicao de usuario e no perfil
   - Correcao do bug em que apenas o menu era traduzido

2. ESQUECI MINHA SENHA
   - Link "Esqueci minha senha" na tela de login
   - Email de redefinicao enviado via SMTP DA EMPRESA (tenant)
   - Token seguro com validade de 1 hora
   - Tela de nova senha com indicador de forca
   - Fallback para SMTP global (variaveis MAIL_*) se tenant nao tiver SMTP

3. CORRECOES
   - babel.cfg corrigido (extensoes Jinja2 obsoletas removidas)
   - requirements.txt atualizado (Flask-Babel, Flask-Mail, Babel)


INSTALACAO AUTOMATICA (RECOMENDADO)
====================================

    1. Copie o pacote para o servidor:
       scp orion_pd_v3_deploy.tar.gz usuario@servidor:/tmp/

    2. No servidor:
       cd /tmp
       tar -xzf orion_pd_v3_deploy.tar.gz
       cd orion_pd_v3_deploy
       sudo bash install_v3.sh /var/www/rd_project_management

    O script faz automaticamente:
       - Backup completo (codigo + banco)
       - Para a aplicacao (systemd/supervisor/pm2/gunicorn)
       - Copia todos os arquivos
       - Instala dependencias novas (Flask-Babel, Flask-Mail)
       - Aplica migracao do banco (colunas de reset de senha)
       - Valida a instalacao
       - Reinicia a aplicacao


INSTALACAO MANUAL (PASSO A PASSO)
==================================

1. BACKUP
---------
    cp -r /var/www/rd_project_management /var/www/backup_$(date +%Y%m%d)

2. PARAR APLICACAO
------------------
    sudo systemctl stop orion-pd     # ou supervisorctl / pm2 / pkill gunicorn

3. INSTALAR DEPENDENCIAS NOVAS
------------------------------
    pip3 install Flask-Babel==4.0.0 Flask-Mail==0.9.1 Babel==2.14.0

4. COPIAR ARQUIVOS
------------------
ARQUIVOS CORE (sobrescrever):
    app.py                    <- auto-migracao + config babel
    models.py                 <- colunas password_reset_token/expires
    extensions.py             <- config de idiomas
    babel.cfg                 <- CORRIGIDO (sem extensoes obsoletas)
    requirements.txt          <- dependencias novas

ROTAS (sobrescrever):
    routes/auth.py            <- rotas forgot-password e reset-password
    routes/users.py           <- campo de idioma no form de usuario
    routes/status_report.py   <- status traduzidos

SERVICOS:
    services/email_service.py <- NOVO - envio via SMTP do tenant

TEMPLATES (sobrescrever TODOS - contem marcadores de traducao):
    templates/                <- TODO o diretorio (75+ arquivos)
    Inclui NOVOS:
      templates/auth/forgot_password.html
      templates/auth/reset_password.html

TRADUCOES (sobrescrever TODO o diretorio):
    translations/pt_BR/LC_MESSAGES/messages.po + .mo
    translations/en/LC_MESSAGES/messages.po + .mo
    translations/es/LC_MESSAGES/messages.po + .mo

DEPLOY:
    deploy/migrate_password_reset.py

5. MIGRACAO DO BANCO
--------------------
    cd /var/www/rd_project_management
    python3 deploy/migrate_password_reset.py

    OBS: A partir desta versao o app.py tambem cria as colunas
    automaticamente no start, entao este passo e opcional.

6. REINICIAR
------------
    sudo systemctl start orion-pd

7. VERIFICAR
------------
    - /login -> deve mostrar link "Esqueci minha senha"
    - Trocar idioma no menu -> TODAS as telas devem traduzir
    - Cadastro de usuario -> deve ter campo Idioma


CONFIGURACAO DO SMTP DO TENANT (OBRIGATORIO P/ RESET DE SENHA)
===============================================================
O email de redefinicao usa o SMTP configurado na EMPRESA do usuario:

    1. Logar como superadmin
    2. Empresas > Editar empresa
    3. Secao "Configuracao de Email":
       - Habilitar envio de emails: SIM
       - Servidor SMTP: smtp.gmail.com (exemplo)
       - Porta: 587  |  Seguranca: TLS
       - Usuario SMTP: email@empresa.com
       - Senha SMTP: (para Gmail, usar Senha de App)
       - Remetente Padrao: Orion P&D <email@empresa.com>

Se o tenant NAO tiver SMTP configurado, o sistema tenta usar as
variaveis de ambiente globais:
    MAIL_SERVER, MAIL_PORT, MAIL_USERNAME, MAIL_PASSWORD,
    MAIL_USE_TLS, MAIL_DEFAULT_SENDER


NOVAS COLUNAS NO BANCO
=======================
    users.password_reset_token    VARCHAR(100)
    users.password_reset_expires  DATETIME

    (criadas automaticamente no start do app ou via
     deploy/migrate_password_reset.py)


ROLLBACK (EM CASO DE PROBLEMAS)
================================
    cp -r /var/www/backup_YYYYMMDD/* /var/www/rd_project_management/
    sudo systemctl restart orion-pd


SUPORTE
========
Logs da aplicacao:
    tail -f /var/log/orion-pd/error.log
    journalctl -u orion-pd -f

Teste de envio de email (no shell python do servidor):
    from app import create_app
    from models import Tenant, User
    from services.email_service import send_email_via_tenant
    app = create_app()
    with app.app_context():
        t = Tenant.query.first()
        ok, err = send_email_via_tenant(t, 'seu@email.com', 'Teste', '<b>OK</b>')
        print(ok, err)

================================================================================
