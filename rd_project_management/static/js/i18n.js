/**
 * Simple i18n (internationalization) for Orion P&D
 * Supports: pt-BR (default), en
 * Auto-translates all visible text on the page
 */

// Portuguese to English translations
const ptToEn = {
    // General
    'Salvar': 'Save',
    'Cancelar': 'Cancel',
    'Excluir': 'Delete',
    'Editar': 'Edit',
    'Adicionar': 'Add',
    'Novo': 'New',
    'Nova': 'New',
    'Buscar': 'Search',
    'Filtrar': 'Filter',
    'Ações': 'Actions',
    'Voltar': 'Back',
    'Fechar': 'Close',
    'Confirmar': 'Confirm',
    'Sim': 'Yes',
    'Não': 'No',
    'Carregando...': 'Loading...',
    'Erro': 'Error',
    'Sucesso': 'Success',
    'Atenção': 'Warning',
    'Obrigatório': 'Required',
    'Opcional': 'Optional',
    'Selecione': 'Select',
    'Nenhum': 'None',
    'Todos': 'All',
    'Total': 'Total',
    'de': 'of',
    'ou': 'or',
    'e': 'and',

    // Auth
    'Entrar': 'Login',
    'Sair': 'Logout',
    'E-mail': 'Email',
    'Senha': 'Password',
    'Lembrar-me': 'Remember me',
    'Esqueceu a senha?': 'Forgot password?',
    'Acesse sua conta': 'Access your account',

    // Menu
    'Início': 'Home',
    'Projetos': 'Projects',
    'Despesas': 'Expenses',
    'Recursos': 'Resources',
    'Cronograma': 'Schedule',
    'Chamadas': 'Calls',
    'Chamadas Públicas': 'Public Calls',
    'Assistente IA': 'AI Assistant',
    'Usuários': 'Users',
    'Usuarios': 'Users',
    'Configurações': 'Settings',
    'Empresas': 'Companies',
    'Programas': 'Programs',
    'Portfolio': 'Portfolio',
    'Meu Perfil': 'My Profile',

    // Projects
    'Novo Projeto': 'New Project',
    'Projeto': 'Project',
    'Código': 'Code',
    'Titulo': 'Title',
    'Título': 'Title',
    'Descrição': 'Description',
    'Status': 'Status',
    'Categoria': 'Category',
    'Orçamento': 'Budget',
    'Data Início': 'Start Date',
    'Data Término': 'End Date',
    'Início': 'Start',
    'Término': 'End',
    'Responsável': 'Responsible',
    'Progresso': 'Progress',
    'Progresso Geral': 'Overall Progress',
    'Ativo': 'Active',
    'Ativos': 'Active',
    'Concluído': 'Completed',
    'Concluido': 'Completed',
    'Cancelado': 'Cancelled',
    'Planejamento': 'Planning',
    'Em Andamento': 'In Progress',
    'Pendente': 'Pending',
    'Atrasado': 'Delayed',
    'Fonte de Financiamento': 'Funding Source',

    // Schedule
    'Marco': 'Milestone',
    'Marcos': 'Milestones',
    'Novo Marco': 'New Milestone',
    'Marcos do Projeto': 'Project Milestones',
    'Predecessora': 'Predecessor',
    'Finish-to-Start': 'Finish-to-Start',
    'Gráfico de Gantt': 'Gantt Chart',
    'Alocação': 'Allocation',
    'Ordem': 'Order',
    'Responsáveis': 'Responsibles',
    'Total alocado': 'Total allocated',
    'A soma das alocações não pode ultrapassar 100%': 'Allocation sum cannot exceed 100%',
    'Adicionar Responsável': 'Add Responsible',
    'A atividade selecionada deve terminar antes desta iniciar': 'Selected activity must finish before this one starts',
    'Importar': 'Import',
    'Exportar': 'Export',

    // Expenses
    'Nova Despesa': 'New Expense',
    'Despesa': 'Expense',
    'Valor': 'Amount',
    'Data': 'Date',
    'Fornecedor': 'Supplier',
    'Nota Fiscal': 'Invoice',
    'Anexos': 'Attachments',
    'Comprovante': 'Receipt',
    'Boleto': 'Payment Slip',

    // Resources
    'Novo Recurso': 'New Resource',
    'Recurso': 'Resource',
    'Nome': 'Name',
    'Tipo': 'Type',
    'Função': 'Role',
    'Custo/Hora': 'Hourly Cost',
    'Custo por Hora': 'Hourly Cost',
    'Horas Alocadas': 'Allocated Hours',
    'Pessoa': 'Person',
    'Equipamento': 'Equipment',
    'Material': 'Material',
    'Equipe': 'Team',

    // Agile
    'Quadro Kanban': 'Kanban Board',
    'Kanban Board': 'Kanban Board',
    'Sprint': 'Sprint',
    'Sprints': 'Sprints',
    'Novo Sprint': 'New Sprint',
    'Sprint Ativo': 'Active Sprint',
    'Story Points': 'Story Points',
    'Prioridade': 'Priority',
    'Baixa': 'Low',
    'Média': 'Medium',
    'Alta': 'High',
    'Crítica': 'Critical',
    'Backlog': 'Backlog',
    'Não Iniciado': 'Not Started',
    'Velocidade': 'Velocity',
    'Burndown': 'Burndown',
    'Meta': 'Goal',
    'Gráficos': 'Charts',
    'Nova Tarefa': 'New Task',
    'Todos os Marcos': 'All Milestones',
    'pts': 'pts',

    // AI
    'Chat IA': 'AI Chat',
    'Gerar Insights': 'Generate Insights',
    'Gerar Insights IA': 'Generate AI Insights',
    'Analisar': 'Analyze',
    'Gerar Relatório': 'Generate Report',
    'Análise de Riscos': 'Risk Analysis',
    'Assistente de Chat': 'Chat Assistant',

    // Timesheet
    'Horas': 'Hours',
    'Atividade': 'Activity',
    'Horas Trabalhadas': 'Worked Hours',
    'Horas Planejadas': 'Planned Hours',
    'Horas Realizadas': 'Realized Hours',

    // Dashboard
    'Projetos Ativos': 'Active Projects',
    'Orçamento Total': 'Total Budget',
    'Despesas Totais': 'Total Expenses',
    'Chamadas Abertas': 'Open Calls',
    'Ações Rápidas': 'Quick Actions',
    'Acoes Rapidas': 'Quick Actions',
    'Próximos Marcos': 'Upcoming Milestones',
    'Proximos Marcos': 'Upcoming Milestones',
    'Notícias Recentes': 'Recent News',
    'Noticias de Editais': 'Call News',
    'Distribuição de Custos': 'Cost Distribution',
    'Distribuicao de Custos por Projeto': 'Cost Distribution by Project',
    'Timeline de Marcos': 'Milestones Timeline',
    'Projetos Encerrando': 'Ending Projects',
    'Ver Projetos': 'View Projects',
    'Ver Todas': 'View All',
    'Ver todas': 'View all',

    // Public Calls
    'Chamada Pública': 'Public Call',
    'Prazo': 'Deadline',
    'Aberta': 'Open',
    'Fechada': 'Closed',
    'Encerrada': 'Closed',

    // Status Report
    'Relatório de Status': 'Status Report',
    'Custo Planejado': 'Planned Cost',
    'Custo Realizado': 'Realized Cost',

    // Common phrases
    'Nenhum dado disponível': 'No data available',
    'Nenhum projeto cadastrado': 'No projects registered',
    'Nenhum marco definido': 'No milestones defined',
    'Nenhuma despesa registrada': 'No expenses registered',
    'Nenhum recurso cadastrado': 'No resources registered',
    'Tem certeza?': 'Are you sure?',
    'Excluir este item?': 'Delete this item?',
    'Excluir este marco?': 'Delete this milestone?',
    'Alterações salvas com sucesso': 'Changes saved successfully',
    'Marco adicionado com sucesso': 'Milestone added successfully',
    'Marco atualizado com sucesso': 'Milestone updated successfully',
    'Marco excluído com sucesso': 'Milestone deleted successfully',
    'Selecione uma opção': 'Select an option',
    'Campo obrigatório': 'Required field',
    'Valor inválido': 'Invalid value',
    'Bem-vindo': 'Welcome',
    'criado com sucesso': 'created successfully',
    'atualizado com sucesso': 'updated successfully',
    'excluído com sucesso': 'deleted successfully',
    'Criar Marco': 'Create Milestone',
    'Defina marcos e etapas para o cronograma do projeto': 'Define milestones and stages for the project schedule',
    'Não atribuído': 'Unassigned',
    'alocação': 'allocation',
    'total': 'total',
    'concluídos': 'completed',
    'progresso médio': 'average progress',

    // Compliance Module
    'Central de Pendências e Conformidade': 'Compliance and Pending Items Center',
    'Conformidade': 'Compliance',
    'Riscos': 'Risks',
    'Risco': 'Risk',
    'Novo Risco': 'New Risk',
    'Editar Risco': 'Edit Risk',
    'Registro de Riscos': 'Risk Registry',
    'Pendências': 'Pending Items',
    'Pendência': 'Pending Item',
    'Nova Pendência': 'New Pending Item',
    'Editar Pendência': 'Edit Pending Item',
    'Não Conformidades': 'Non-Conformities',
    'Não Conformidade': 'Non-Conformity',
    'Nova NC': 'New NC',
    'Editar Não Conformidade': 'Edit Non-Conformity',
    'Bugs': 'Bugs',
    'Bug': 'Bug',
    'Novo Bug': 'New Bug',
    'Editar Bug': 'Edit Bug',
    'Registro de Bugs': 'Bug Registry',
    'Ações Corretivas': 'Corrective Actions',
    'Ação Corretiva': 'Corrective Action',
    'Nova Ação': 'New Action',
    'Editar Ação Corretiva': 'Edit Corrective Action',
    'Probabilidade': 'Probability',
    'Impacto': 'Impact',
    'Score': 'Score',
    'Severidade': 'Severity',
    'Ambiente': 'Environment',
    'Desenvolvimento': 'Development',
    'Homologação': 'Staging',
    'Produção': 'Production',
    'Tipo': 'Type',
    'Causa Raiz': 'Root Cause',
    'Plano Corretivo': 'Corrective Plan',
    'Plano de Mitigação': 'Mitigation Plan',
    'Plano de Contingência': 'Contingency Plan',
    'Estratégia de Resposta': 'Response Strategy',
    'Evitar': 'Avoid',
    'Mitigar': 'Mitigate',
    'Transferir': 'Transfer',
    'Aceitar': 'Accept',
    'Data Limite': 'Due Date',
    'Data Identificação': 'Identified Date',
    'Data Resolução': 'Resolution Date',
    'Data Fechamento': 'Closure Date',
    'Data Conclusão': 'Completion Date',
    'Identificado': 'Identified',
    'Analisado': 'Analyzed',
    'Em Tratamento': 'In Treatment',
    'Mitigado': 'Mitigated',
    'Verificação': 'Verification',
    'Em Análise': 'In Analysis',
    'Em Correção': 'In Correction',
    'Teste': 'Test',
    'Resolvido': 'Resolved',
    'Resolvida': 'Resolved',
    'Cancelada': 'Cancelled',
    'Planejada': 'Planned',
    'Concluída': 'Completed',
    'Verificada': 'Verified',
    'Eficácia': 'Effectiveness',
    'Eficaz': 'Effective',
    'Parcialmente Eficaz': 'Partially Effective',
    'Não Eficaz': 'Not Effective',
    'Corretiva': 'Corrective',
    'Preventiva': 'Preventive',
    'Melhoria': 'Improvement',
    'Passos para Reproduzir': 'Steps to Reproduce',
    'Comportamento Esperado': 'Expected Behavior',
    'Comportamento Atual': 'Actual Behavior',
    'Evidência': 'Evidence',
    'Notas de Resolução': 'Resolution Notes',
    'Notas de Verificação': 'Verification Notes',
    'Observações de Resolução': 'Resolution Notes',
    'Últimos Itens Registrados': 'Recent Items',
    'Resumo por Projeto': 'Summary by Project',
    'Vincule esta ação a um item de origem': 'Link this action to a source item',
    'Processo': 'Process',
    'Produto': 'Product',
    'Documentação': 'Documentation',
    'Auditoria': 'Audit',
    'Cliente': 'Client',
    'Regulatório': 'Regulatory',
    'Técnico': 'Technical',
    'Financeiro': 'Financial',
    'Cronograma': 'Schedule',
    'Recursos': 'Resources',
    'Escopo': 'Scope',
    'Externo': 'External',
    'Organizacional': 'Organizational',
    'Muito Baixa': 'Very Low',
    'Muito Baixo': 'Very Low',
    'Muito Alta': 'Very High',
    'Muito Alto': 'Very High'
};

// Reverse dictionary (English to Portuguese)
const enToPt = Object.fromEntries(
    Object.entries(ptToEn).map(([pt, en]) => [en, pt])
);

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
 * Translate a string based on current language
 */
function _(text) {
    if (currentLang === 'en') {
        return ptToEn[text] || text;
    }
    return text; // PT-BR is the source
}

/**
 * Translate text content
 */
function translateText(text) {
    if (!text || typeof text !== 'string') return text;

    const trimmed = text.trim();
    if (!trimmed) return text;

    if (currentLang === 'en') {
        // Translate PT -> EN
        // First try exact match
        if (ptToEn[trimmed]) {
            return text.replace(trimmed, ptToEn[trimmed]);
        }
        // Then try case-insensitive match
        const lowerKey = Object.keys(ptToEn).find(k => k.toLowerCase() === trimmed.toLowerCase());
        if (lowerKey) {
            return text.replace(trimmed, ptToEn[lowerKey]);
        }
    }
    return text;
}

/**
 * Set language and reload page to apply translations
 */
function setLanguage(lang) {
    currentLang = lang;
    localStorage.setItem('orion_lang', lang);

    // Update flag indicator
    document.querySelectorAll('.lang-flag').forEach(el => {
        el.classList.remove('active');
    });
    document.querySelector(`.lang-flag[data-lang="${lang}"]`)?.classList.add('active');

    // Reload page to apply translations
    location.reload();
}

/**
 * Auto-translate all visible text on the page
 */
function translatePage() {
    if (currentLang === 'pt-BR') return; // Source language, no translation needed

    // Translate text nodes
    const walker = document.createTreeWalker(
        document.body,
        NodeFilter.SHOW_TEXT,
        {
            acceptNode: function(node) {
                // Skip script and style tags
                const parent = node.parentNode;
                if (parent.tagName === 'SCRIPT' || parent.tagName === 'STYLE' || parent.tagName === 'NOSCRIPT') {
                    return NodeFilter.FILTER_REJECT;
                }
                // Skip empty nodes
                if (!node.textContent.trim()) {
                    return NodeFilter.FILTER_REJECT;
                }
                return NodeFilter.FILTER_ACCEPT;
            }
        }
    );

    const textNodes = [];
    while (walker.nextNode()) {
        textNodes.push(walker.currentNode);
    }

    textNodes.forEach(node => {
        const original = node.textContent;
        const translated = translateText(original);
        if (translated !== original) {
            node.textContent = translated;
        }
    });

    // Translate placeholders
    document.querySelectorAll('[placeholder]').forEach(el => {
        const original = el.placeholder;
        const translated = translateText(original);
        if (translated !== original) {
            el.placeholder = translated;
        }
    });

    // Translate titles
    document.querySelectorAll('[title]').forEach(el => {
        const original = el.title;
        const translated = translateText(original);
        if (translated !== original) {
            el.title = translated;
        }
    });

    // Translate button values
    document.querySelectorAll('input[type="submit"], input[type="button"]').forEach(el => {
        const original = el.value;
        const translated = translateText(original);
        if (translated !== original) {
            el.value = translated;
        }
    });

    // Translate select options
    document.querySelectorAll('select option').forEach(el => {
        const original = el.textContent;
        const translated = translateText(original);
        if (translated !== original) {
            el.textContent = translated;
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

    // Auto-translate page if English is selected
    if (currentLang === 'en') {
        // Small delay to ensure page is fully rendered
        setTimeout(translatePage, 100);
    }
});

// Export for use in other scripts
window.i18n = { _, setLanguage, translateText, currentLang: () => currentLang };
