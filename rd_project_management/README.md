# Orion Gestão de P&D

Sistema de Gestão de Projetos de Pesquisa e Desenvolvimento com funcionalidades de Inteligência Artificial.

## Proposta de Valor

O **Orion P&D** é uma plataforma multiempresa para gestão de projetos de P&D que integra controle de despesas, cronogramas, recursos humanos e documentação em um único ambiente. O sistema monitora automaticamente chamadas públicas da FINEP, BNDES e FAPESC, alertando empresas sobre oportunidades de fomento. Com inteligência artificial integrada, analisa editais, sugere matches entre projetos e chamadas, e gera propostas de submissão automaticamente. A plataforma oferece rastreabilidade completa de gastos com anexação de boletos, notas fiscais e comprovantes, facilitando prestações de contas aos órgãos de fomento.

### Benefícios

**Para o Estado:** Visibilidade em tempo real dos projetos financiados, rastreabilidade completa de gastos com documentos comprobatórios anexados, e relatórios automáticos que facilitam a fiscalização e reduzem fraudes na aplicação de recursos públicos.

**Para as Empresas:** Alertas automáticos de chamadas públicas compatíveis com seus projetos, geração de propostas com IA que aumenta chances de aprovação, e gestão simplificada de prestação de contas que reduz burocracia e retrabalho.

**Resultado:** Mais empresas acessando recursos, maior transparência na execução, e melhor retorno do investimento público em inovação.

## Visão Geral

O Orion P&D é uma solução completa para gerenciamento de projetos de pesquisa e desenvolvimento, oferecendo:

- Gestão de projetos com orçamento, cronograma e recursos
- Controle de despesas com anexos (boletos, notas fiscais, comprovantes)
- Acompanhamento de chamadas públicas (FINEP, BNDES, FAPESC)
- Funcionalidades de IA para análise, automação e geração de propostas
- Multi-tenancy com isolamento de dados por empresa
- Home page com insights do setor e notícias de P&D

## Funcionalidades Principais

### Home Page
- Dashboard com nome da empresa e estatísticas
- Insights do setor gerados por IA
- Chamadas públicas recentes
- Próximos milestones dos projetos

### Gestão de Projetos
- Cadastro de projetos com código, título, descrição e orçamento
- Definição de datas de início e fim
- Vinculação de responsável
- Acompanhamento de status (Planejamento, Em Andamento, Concluído, Cancelado)
- Upload de documentos (PDF, Word, Excel, PowerPoint)

### Controle Financeiro
- Registro de despesas por categoria
- **Anexos de despesas:** boletos, notas fiscais e comprovantes de pagamento
- Acompanhamento de orçamento vs. gastos
- Relatórios de execução financeira
- Rastreabilidade completa para prestação de contas

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
- Integração automática com FINEP, BNDES e FAPESC
- Cadastro manual de editais
- Vinculação de projetos a chamadas
- **Geração de propostas com IA**
- Painel de notícias de P&D na tela de login

### Inteligência Artificial

O sistema integra a API do Claude (Anthropic) para:

| Funcionalidade | Descrição |
|----------------|-----------|
| **Análise de Editais** | Extrai informações de PDFs: prazos, valores, requisitos, itens financiáveis |
| **Matching Projeto-Edital** | Encontra editais compatíveis com cada projeto e sugere adaptações |
| **Geração de Propostas** | Cria propostas completas para submissão em chamadas públicas |
| **Geração de Relatórios** | Cria relatórios técnicos parciais ou finais automaticamente |
| **Análise de Riscos** | Identifica riscos de orçamento, cronograma e recursos |
| **Assistente de Chat** | Responde perguntas sobre projetos em linguagem natural |
| **Insights do Setor** | Gera insights de P&D personalizados para cada empresa |

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

## Migração do Banco de Dados

### Atualização para versão com anexos de despesas

Para bancos de dados existentes, execute:

```bash
cd rd_project_management
python add_expense_attachments_table.py
```

**Saída esperada:**
```
Table 'expense_attachments' created successfully!
```

## Estrutura do Projeto

```
rd_project_management/
├── app.py                          # Aplicação principal Flask
├── models.py                       # Modelos do banco de dados
├── requirements.txt                # Dependências Python
├── backup_banco.bat                # Script de backup (Windows)
├── add_expense_attachments_table.py # Migração de anexos
│
├── instance/
│   └── rd_projects.db              # Banco de dados SQLite
│
├── routes/
│   ├── ai.py                       # Rotas de IA e geração de propostas
│   ├── auth.py                     # Autenticação
│   ├── home.py                     # Home page com insights
│   ├── projects.py                 # Projetos
│   ├── expenses.py                 # Despesas e anexos
│   ├── resources.py                # Recursos
│   ├── schedule.py                 # Cronograma
│   ├── timesheet.py                # Timesheet
│   ├── public_calls.py             # Chamadas públicas
│   ├── users.py                    # Usuários
│   └── tenants.py                  # Empresas (tenants)
│
├── services/
│   ├── ai_service.py               # Serviços de IA
│   ├── tenant_utils.py             # Utilitários multi-tenant
│   ├── finep_scraper.py            # Scraper FINEP
│   ├── bndes_scraper.py            # Scraper BNDES
│   └── fapesc_scraper.py           # Scraper FAPESC
│
├── templates/
│   ├── base.html                   # Template base
│   ├── home/
│   │   └── dashboard.html          # Home page
│   ├── ai/
│   │   ├── dashboard.html          # Dashboard IA
│   │   └── proposal.html           # Geração de propostas
│   ├── auth/
│   │   └── login.html              # Login com notícias P&D
│   ├── projects/                   # Projetos
│   ├── expenses/                   # Despesas com anexos
│   ├── public_calls/               # Chamadas públicas
│   └── ...
│
├── static/
│   ├── css/style.css               # Estilos (tema Orion)
│   └── js/app.js                   # JavaScript
│
└── uploads/                        # Documentos e anexos enviados
    └── {tenant_id}/
        ├── *.pdf                   # Documentos de projetos
        └── expenses/               # Anexos de despesas
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

## Anexos de Despesas

O sistema permite anexar documentos comprobatórios em cada despesa:

| Tipo | Descrição |
|------|-----------|
| **Boleto** | Boleto bancário para pagamento |
| **Nota Fiscal** | NF-e, NFS-e ou nota fiscal convencional |
| **Comprovante** | Comprovante de pagamento/transferência |

- **Formatos aceitos:** PDF, JPG, PNG, Word
- **Limite:** 5 anexos por despesa
- **Armazenamento:** Organizado por tenant/empresa

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
| Geração de Propostas | claude-sonnet-4-20250514 | 4000 |
| Relatórios | claude-sonnet-4-20250514 | 4000 |
| Riscos | claude-sonnet-4-20250514 | 2000 |
| Chat | claude-sonnet-4-20250514 | 1500 |
| Insights | claude-sonnet-4-20250514 | 2000 |

## Suporte

Para reportar problemas ou sugerir melhorias:
- Abra uma issue no repositório
- Contate o administrador do sistema

---

**Versão:** 1.1  
**Última atualização:** Maio 2026
