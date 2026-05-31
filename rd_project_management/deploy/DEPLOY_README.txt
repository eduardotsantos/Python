================================================================================
                    PACOTE DE DEPLOY - ORION P&D v2.0
                    Central de Conformidade + PMO IA
================================================================================

NOVOS MÓDULOS
-------------
1. Central de Pendências e Conformidade (/compliance)
   - Riscos, Pendências, Não Conformidades, Bugs, Ações Corretivas

2. Orion Autônomos PMO (/pmo)
   - 11 Agentes IA para gestão autônoma de projetos
   - Daily Executive AI (briefing diário)
   - Leitor de Atas com extração automática


PASSO A PASSO PARA DEPLOY
=========================

1. BACKUP (IMPORTANTE!)
------------------------
Antes de qualquer coisa, faça backup:

    cp -r /var/www/rd_project_management /var/www/backup_$(date +%Y%m%d)


2. COPIAR ARQUIVOS MODIFICADOS
-------------------------------
Copie estes arquivos do pacote para o servidor:

ARQUIVOS CORE (sobrescrever):
    app.py
    models.py
    static/js/i18n.js
    templates/base.html

NOVOS DIRETÓRIOS (criar e copiar):
    agents/                          -> TODO o diretório
    routes/compliance.py             -> arquivo novo
    routes/pmo_agents.py             -> arquivo novo
    templates/compliance/            -> TODO o diretório
    templates/pmo_agents/            -> TODO o diretório


3. CRIAR DIRETÓRIOS NO SERVIDOR
--------------------------------
    mkdir -p /var/www/rd_project_management/agents
    mkdir -p /var/www/rd_project_management/templates/compliance/risks
    mkdir -p /var/www/rd_project_management/templates/compliance/pending
    mkdir -p /var/www/rd_project_management/templates/compliance/nc
    mkdir -p /var/www/rd_project_management/templates/compliance/bugs
    mkdir -p /var/www/rd_project_management/templates/compliance/actions
    mkdir -p /var/www/rd_project_management/templates/pmo_agents


4. PARAR APLICAÇÃO
-------------------
    # Systemd:
    sudo systemctl stop orion-pd

    # Supervisor:
    sudo supervisorctl stop orion-pd

    # PM2:
    pm2 stop orion-pd

    # Gunicorn direto:
    pkill -f gunicorn


5. EXECUTAR MIGRATION
----------------------
    cd /var/www/rd_project_management
    python3 deploy/migrate_compliance_pmo.py

    OU se preferir manualmente no Python:

    python3
    >>> from app import create_app
    >>> from models import db
    >>> app = create_app()
    >>> with app.app_context():
    ...     db.create_all()


6. REINICIAR APLICAÇÃO
-----------------------
    # Systemd:
    sudo systemctl start orion-pd

    # Supervisor:
    sudo supervisorctl start orion-pd

    # PM2:
    pm2 start orion-pd

    # Gunicorn:
    gunicorn -w 4 -b 0.0.0.0:5000 "app:create_app()"


7. VERIFICAR
-------------
Acesse no navegador:
    - /compliance → Deve mostrar dashboard de conformidade
    - /pmo → Deve mostrar dashboard dos agentes IA


LISTA COMPLETA DE ARQUIVOS
===========================

ARQUIVOS MODIFICADOS:
    app.py
    models.py
    static/js/i18n.js
    templates/base.html

NOVOS ARQUIVOS - AGENTS (11 arquivos):
    agents/__init__.py
    agents/base.py
    agents/orchestrator.py
    agents/health_agent.py
    agents/risk_agent.py
    agents/financial_agent.py
    agents/schedule_agent.py
    agents/resource_agent.py
    agents/quality_agent.py
    agents/compliance_agent.py
    agents/communication_agent.py
    agents/lessons_agent.py
    agents/advisor_agent.py
    agents/minutes_reader.py

NOVOS ARQUIVOS - ROUTES:
    routes/compliance.py
    routes/pmo_agents.py

NOVOS ARQUIVOS - TEMPLATES COMPLIANCE (12 arquivos):
    templates/compliance/dashboard.html
    templates/compliance/risks/list.html
    templates/compliance/risks/form.html
    templates/compliance/pending/list.html
    templates/compliance/pending/form.html
    templates/compliance/nc/list.html
    templates/compliance/nc/form.html
    templates/compliance/bugs/list.html
    templates/compliance/bugs/form.html
    templates/compliance/actions/list.html
    templates/compliance/actions/form.html

NOVOS ARQUIVOS - TEMPLATES PMO (5 arquivos):
    templates/pmo_agents/dashboard.html
    templates/pmo_agents/briefing.html
    templates/pmo_agents/agent_result.html
    templates/pmo_agents/action_center.html
    templates/pmo_agents/minutes_parser.html


ROLLBACK (EM CASO DE PROBLEMAS)
================================
    cp -r /var/www/backup_YYYYMMDD/* /var/www/rd_project_management/
    sudo systemctl restart orion-pd


NOVAS TABELAS NO BANCO
=======================
    - risks
    - pending_items
    - non_conformities
    - bugs
    - corrective_actions

Todas as tabelas incluem tenant_id para multi-tenancy.


SUPORTE
========
Em caso de dúvidas, verifique os logs:
    tail -f /var/log/orion-pd/error.log

================================================================================
