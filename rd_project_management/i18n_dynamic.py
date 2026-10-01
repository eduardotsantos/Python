"""
Dynamic database values that need translation.

These strings are stored in the database (status fields, types, roles) and
rendered via {{ _(variable) }} in templates, so pybabel cannot find them by
scanning the templates. Listing them here keeps them in the catalogs across
`pybabel extract` / `pybabel update` runs.

This module is never imported at runtime.
"""

def _(s):  # placeholder so this file is valid Python for pybabel's parser
    return s


DYNAMIC_STRINGS = [
    # Project.value_type
    _('ROI'),
    _('Economia'),
    _('Receita'),
    _('Estratégico'),

    # Project.value_status
    _('Não iniciado'),
    _('Em captura'),
    _('Parcial'),
    _('Realizado'),

    # Stakeholder.role
    _('Patrocinador'),
    _('Cliente'),
    _('Usuário Final'),
    _('Fornecedor'),
    _('Parceiro'),
    _('Regulador'),
    _('Equipe Técnica'),
    _('Consultor'),
    _('Financiador'),
    _('Outro'),

    # Stakeholder.influence_level / interest_level
    _('Baixo'),
    _('Médio'),
    _('Alto'),
    _('Muito Alto'),

    # Stakeholder.power_interest_quadrant
    _('Gerenciar de Perto'),
    _('Manter Satisfeito'),
    _('Manter Informado'),
    _('Monitorar'),

    # Project.status
    _('Planejamento'),
    _('Em Execução'),
    _('Em Andamento'),
    _('Pausado'),
    _('Concluído'),
    _('Cancelado'),

    # Expense.category
    _('Bolsas'),
    _('Material de Consumo'),
    _('Equipamentos'),
    _('Serviços de Terceiros'),
    _('Viagens'),
    _('Mão de Obra'),
    _('Outros'),

    # Expense.status
    _('Pendente'),
    _('Aprovada'),
    _('Paga'),
    _('Rejeitada'),
]
