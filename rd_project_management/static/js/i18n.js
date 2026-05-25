/**
 * Simple i18n (internationalization) for Orion P&D
 * Supports: pt-BR (default), en
 */

const translations = {
    'pt-BR': {
        // General
        'Save': 'Salvar',
        'Cancel': 'Cancelar',
        'Delete': 'Excluir',
        'Edit': 'Editar',
        'Add': 'Adicionar',
        'New': 'Novo',
        'Search': 'Buscar',
        'Filter': 'Filtrar',
        'Actions': 'Ações',
        'Back': 'Voltar',
        'Close': 'Fechar',
        'Confirm': 'Confirmar',
        'Yes': 'Sim',
        'No': 'Não',
        'Loading...': 'Carregando...',
        'Error': 'Erro',
        'Success': 'Sucesso',
        'Warning': 'Atenção',

        // Auth
        'Login': 'Entrar',
        'Logout': 'Sair',
        'Email': 'E-mail',
        'Password': 'Senha',
        'Remember me': 'Lembrar-me',
        'Forgot password?': 'Esqueceu a senha?',

        // Menu
        'Home': 'Início',
        'Projects': 'Projetos',
        'Expenses': 'Despesas',
        'Resources': 'Recursos',
        'Schedule': 'Cronograma',
        'Timesheet': 'Timesheet',
        'Public Calls': 'Chamadas Públicas',
        'AI Assistant': 'Assistente IA',
        'Users': 'Usuários',
        'Settings': 'Configurações',
        'Agile': 'Ágil',
        'Kanban': 'Kanban',
        'Sprints': 'Sprints',
        'Charts': 'Gráficos',

        // Projects
        'New Project': 'Novo Projeto',
        'Project': 'Projeto',
        'Code': 'Código',
        'Title': 'Título',
        'Description': 'Descrição',
        'Status': 'Status',
        'Category': 'Categoria',
        'Budget': 'Orçamento',
        'Start Date': 'Data Início',
        'End Date': 'Data Término',
        'Responsible': 'Responsável',
        'Progress': 'Progresso',
        'Active': 'Ativo',
        'Completed': 'Concluído',
        'Cancelled': 'Cancelado',
        'Planning': 'Planejamento',
        'In Progress': 'Em Andamento',

        // Schedule
        'Milestone': 'Marco',
        'Milestones': 'Marcos',
        'New Milestone': 'Novo Marco',
        'Predecessor': 'Predecessora',
        'Finish-to-Start': 'Término-para-Início',
        'Gantt Chart': 'Gráfico de Gantt',
        'Overall Progress': 'Progresso Geral',
        'Allocation': 'Alocação',
        'Order': 'Ordem',

        // Expenses
        'New Expense': 'Nova Despesa',
        'Expense': 'Despesa',
        'Amount': 'Valor',
        'Date': 'Data',
        'Supplier': 'Fornecedor',
        'Receipt': 'Nota Fiscal',
        'Attachments': 'Anexos',

        // Resources
        'New Resource': 'Novo Recurso',
        'Resource': 'Recurso',
        'Name': 'Nome',
        'Type': 'Tipo',
        'Role': 'Função',
        'Hourly Cost': 'Custo/Hora',
        'Hours Allocated': 'Horas Alocadas',
        'Person': 'Pessoa',
        'Equipment': 'Equipamento',
        'Material': 'Material',
        'Team': 'Equipe',

        // Agile
        'Kanban Board': 'Quadro Kanban',
        'Sprint': 'Sprint',
        'New Sprint': 'Novo Sprint',
        'Story Points': 'Story Points',
        'Priority': 'Prioridade',
        'Low': 'Baixa',
        'Medium': 'Média',
        'High': 'Alta',
        'Critical': 'Crítica',
        'Backlog': 'Backlog',
        'Not Started': 'Não Iniciado',
        'Done': 'Concluído',
        'Velocity': 'Velocidade',
        'Burndown': 'Burndown',
        'Goal': 'Meta',
        'Active Sprint': 'Sprint Ativo',

        // AI
        'AI Chat': 'Chat IA',
        'Generate Insights': 'Gerar Insights',
        'Analyze': 'Analisar',
        'Generate Report': 'Gerar Relatório',
        'Risk Analysis': 'Análise de Riscos',

        // Timesheet
        'Hours': 'Horas',
        'Activity': 'Atividade',
        'Worked Hours': 'Horas Trabalhadas',
        'Planned Hours': 'Horas Planejadas',
        'Realized Hours': 'Horas Realizadas',

        // Status
        'Pending': 'Pendente',
        'Approved': 'Aprovado',
        'Rejected': 'Rejeitado',
        'Delayed': 'Atrasado',
        'Open': 'Aberta',
        'Closed': 'Fechada',

        // Dashboard
        'Active Projects': 'Projetos Ativos',
        'Total Budget': 'Orçamento Total',
        'Total Expenses': 'Despesas',
        'Open Calls': 'Chamadas Abertas',
        'Quick Actions': 'Ações Rápidas',
        'Upcoming Milestones': 'Próximos Marcos',
        'Recent News': 'Notícias Recentes',
        'Cost Distribution': 'Distribuição de Custos',
        'Timeline': 'Timeline',

        // Messages
        'Are you sure?': 'Tem certeza?',
        'Delete this item?': 'Excluir este item?',
        'Changes saved successfully': 'Alterações salvas com sucesso',
        'Error saving changes': 'Erro ao salvar alterações',
        'No data available': 'Nenhum dado disponível',
        'Select an option': 'Selecione uma opção',
        'Required field': 'Campo obrigatório',
        'Invalid value': 'Valor inválido',
        'Allocation cannot exceed 100%': 'A soma das alocações não pode ultrapassar 100%',
        'Total allocated': 'Total alocado'
    },

    'en': {
        // All keys map to themselves in English (source language)
    }
};

// Current language
let currentLang = localStorage.getItem('orion_lang') || 'pt-BR';

/**
 * Translate a string
 */
function _(text) {
    if (currentLang === 'en') {
        return text; // English is the source
    }
    return translations[currentLang]?.[text] || text;
}

/**
 * Set language and reload translations
 */
function setLanguage(lang) {
    currentLang = lang;
    localStorage.setItem('orion_lang', lang);
    translatePage();

    // Update flag indicator
    document.querySelectorAll('.lang-flag').forEach(el => {
        el.classList.remove('active');
    });
    document.querySelector(`.lang-flag[data-lang="${lang}"]`)?.classList.add('active');
}

/**
 * Translate all elements with data-i18n attribute
 */
function translatePage() {
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        if (currentLang === 'pt-BR') {
            el.textContent = translations['pt-BR'][key] || key;
        } else {
            el.textContent = key;
        }
    });

    // Translate placeholders
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
        const key = el.getAttribute('data-i18n-placeholder');
        if (currentLang === 'pt-BR') {
            el.placeholder = translations['pt-BR'][key] || key;
        } else {
            el.placeholder = key;
        }
    });

    // Translate titles
    document.querySelectorAll('[data-i18n-title]').forEach(el => {
        const key = el.getAttribute('data-i18n-title');
        if (currentLang === 'pt-BR') {
            el.title = translations['pt-BR'][key] || key;
        } else {
            el.title = key;
        }
    });
}

/**
 * Initialize i18n on page load
 */
document.addEventListener('DOMContentLoaded', function() {
    // Set initial language indicator
    document.querySelector(`.lang-flag[data-lang="${currentLang}"]`)?.classList.add('active');

    // Add click handlers to language flags
    document.querySelectorAll('.lang-flag').forEach(el => {
        el.addEventListener('click', function() {
            setLanguage(this.dataset.lang);
        });
    });
});

// Export for use in other scripts
window.i18n = { _, setLanguage, currentLang: () => currentLang };
