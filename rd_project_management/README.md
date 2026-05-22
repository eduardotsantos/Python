# Orion Gestão de P&D

Sistema de Gestão de Projetos de Pesquisa e Desenvolvimento com funcionalidades de Inteligência Artificial.

## Visão Geral

O Orion P&D é uma solução completa para gerenciamento de projetos de pesquisa e desenvolvimento, oferecendo:

- Gestão de projetos com orçamento, cronograma e recursos
- Controle de despesas e timesheet
- Acompanhamento de chamadas públicas (FINEP, BNDES)
- Funcionalidades de IA para análise e automação
- Multi-tenancy com isolamento de dados por empresa

## Funcionalidades Principais

### Gestão de Projetos
- Cadastro de projetos com código, título, descrição e orçamento
- Definição de datas de início e fim
- Vinculação de responsável
- Acompanhamento de status (Planejamento, Em Andamento, Concluído, Cancelado)
- Upload de documentos (PDF, Word, Excel, PowerPoint)

### Controle Financeiro
- Registro de despesas por categoria
- Acompanhamento de orçamento vs. gastos
- Relatórios de execução financeira

### Recursos e Equipe
- Cadastro de recursos humanos e materiais
- Alocação de horas por projeto
- Controle de custos por recurso

### Cronograma
- Marcos/milestones do projeto
- Acompanhamento de progresso (%)
- Visualização de cronograma

### Timesheet
- Registro de horas trabalhadas
- Vinculação com atividades e marcos
- Relatório de horas por projeto/usuário

### Chamadas Públicas
- Integração com FINEP e BNDES
- Cadastro manual de editais
- Vinculação de projetos a chamadas

### Inteligência Artificial

O sistema integra a API do Claude (Anthropic) para:

| Funcionalidade | Descrição |
|----------------|-----------|
| **Análise de Editais** | Extrai informações de PDFs: prazos, valores, requisitos, itens financiáveis |
| **Matching Projeto-Edital** | Encontra editais compatíveis com cada projeto e sugere adaptações |
| **Geração de Relatórios** | Cria relatórios técnicos parciais ou finais automaticamente |
| **Análise de Riscos** | Identifica riscos de orçamento, cronograma e recursos |
| **Assistente de Chat** | Responde perguntas sobre projetos em linguagem natural |

## Requisitos

### Software
- Python 3.10+
- Flask 3.0+
- SQLite (padrão) ou PostgreSQL

### Dependências Python
```
Flask==3.0.0
Flask-SQLAlchemy==3.1.1
Flask-Login==0.6.3
Flask-WTF==1.2.1
Werkzeug==3.0.1
requests==2.31.0
beautifulsoup4==4.12.2
APScheduler==3.10.4
openpyxl==3.1.2
anthropic>=0.18.0
PyMuPDF>=1.23.0
```

## Instalação

### 1. Clonar o Repositório
```bash
git clone <url-do-repositorio>
cd rd_project_management
```

### 2. Criar Ambiente Virtual
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Instalar Dependências
```bash
pip install -r requirements.txt
```

### 4. Configurar Variáveis de Ambiente

**Windows (PowerShell):**
```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-sua-chave-aqui"
$env:SECRET_KEY = "sua-chave-secreta-aqui"
```

**Linux/Mac:**
```bash
export ANTHROPIC_API_KEY="sk-ant-sua-chave-aqui"
export SECRET_KEY="sua-chave-secreta-aqui"
```

### 5. Executar a Aplicação
```bash
python app.py
```

Acesse: `http://localhost:5000`

### 6. Login Inicial
- **Usuário:** superadmin
- **Senha:** super123

> ⚠️ **Importante:** Altere a senha do superadmin após o primeiro acesso.

## Estrutura do Projeto

```
rd_project_management/
├── app.py                 # Aplicação principal Flask
├── models.py              # Modelos do banco de dados
├── requirements.txt       # Dependências Python
├── backup_banco.bat       # Script de backup (Windows)
│
├── instance/
│   └── rd_projects.db     # Banco de dados SQLite
│
├── routes/
│   ├── ai.py              # Rotas de IA
│   ├── auth.py            # Autenticação
│   ├── projects.py        # Projetos
│   ├── expenses.py        # Despesas
│   ├── resources.py       # Recursos
│   ├── schedule.py        # Cronograma
│   ├── timesheet.py       # Timesheet
│   ├── public_calls.py    # Chamadas públicas
│   ├── users.py           # Usuários
│   └── tenants.py         # Empresas (tenants)
│
├── services/
│   ├── ai_service.py      # Serviços de IA
│   ├── tenant_utils.py    # Utilitários multi-tenant
│   ├── finep_scraper.py   # Scraper FINEP
│   └── bndes_scraper.py   # Scraper BNDES
│
├── templates/
│   ├── base.html          # Template base
│   ├── ai/                # Templates de IA
│   ├── auth/              # Login
│   ├── projects/          # Projetos
│   ├── expenses/          # Despesas
│   └── ...
│
├── static/
│   ├── css/style.css      # Estilos
│   └── js/app.js          # JavaScript
│
└── uploads/               # Documentos enviados
```

## Multi-Tenancy

O sistema suporta múltiplas empresas (tenants) com isolamento completo de dados:

- Cada empresa tem seus próprios projetos, usuários e dados
- Superadmin gerencia todas as empresas
- Usuários só acessam dados de sua empresa

### Papéis de Usuário
| Papel | Permissões |
|-------|------------|
| **superadmin** | Acesso total, gerencia empresas |
| **admin** | Gerencia usuários da empresa |
| **manager** | Acesso a relatórios e usuários |
| **user** | Acesso básico aos projetos |

## Backup do Banco de Dados

### Script Automático (Windows)

1. Edite o arquivo `backup_banco.bat`:
```bat
set APP_DIR=C:\caminho\para\rd_project_management
set BACKUP_DIR=C:\backups\orion_pd
set MANTER_DIAS=30
```

2. Agende no **Agendador de Tarefas do Windows**:
   - Gatilho: Diário às 02:00
   - Ação: Executar `backup_banco.bat`

### Backup Manual
```bash
copy instance\rd_projects.db backup_rd_projects.db
```

## Configuração da IA

Para habilitar as funcionalidades de IA:

1. Obtenha uma API key em: https://console.anthropic.com/settings/keys

2. Configure a variável de ambiente:
```powershell
# Windows (permanente)
[System.Environment]::SetEnvironmentVariable("ANTHROPIC_API_KEY", "sk-ant-sua-chave", "User")
```

3. Reinicie a aplicação

## Produção

### Recomendações
- Use PostgreSQL em vez de SQLite
- Configure HTTPS com certificado SSL
- Use Gunicorn ou uWSGI como servidor WSGI
- Configure backup automático do banco
- Defina SECRET_KEY forte e única

### Exemplo com Gunicorn
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

## API de IA - Modelos Utilizados

| Funcionalidade | Modelo | Tokens Máx |
|----------------|--------|------------|
| Análise de Editais | claude-sonnet-4-20250514 | 2000 |
| Matching | claude-sonnet-4-20250514 | 2000 |
| Relatórios | claude-sonnet-4-20250514 | 4000 |
| Riscos | claude-sonnet-4-20250514 | 2000 |
| Chat | claude-sonnet-4-20250514 | 1500 |

## Suporte

Para reportar problemas ou sugerir melhorias:
- Abra uma issue no repositório
- Contate o administrador do sistema

---

**Versão:** 1.0  
**Última atualização:** Maio 2026
