"""
Home page routes for Orion P&D.
Provides dashboard with company insights, public calls news, and quick stats.
"""
import os
from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func
from datetime import datetime, timedelta

from models import db, Project, PublicCall, Expense, Milestone, Tenant
from services.tenant_utils import tenant_required, get_current_tenant_id
from services.ai_service import get_anthropic_client

home_bp = Blueprint('home', __name__)


@home_bp.route('/home')
@login_required
@tenant_required
def dashboard():
    """Main dashboard/home page."""
    tenant_id = get_current_tenant_id()
    tenant = current_user.tenant

    # Get project stats
    if current_user.is_superadmin():
        projects = Project.query.all()
        total_projects = len(projects)
        active_projects = Project.query.filter(Project.status.in_(['Em Andamento', 'Planejamento'])).count()
    else:
        projects = Project.query.filter_by(tenant_id=tenant_id).all()
        total_projects = len(projects)
        active_projects = Project.query.filter_by(tenant_id=tenant_id).filter(
            Project.status.in_(['Em Andamento', 'Planejamento'])
        ).count()

    # Get total budget and expenses
    total_budget = sum(p.budget or 0 for p in projects)
    if tenant_id:
        total_expenses = db.session.query(func.sum(Expense.amount)).filter_by(tenant_id=tenant_id).scalar() or 0
    else:
        total_expenses = db.session.query(func.sum(Expense.amount)).scalar() or 0

    # Get upcoming milestones (next 30 days)
    today = datetime.now().date()
    next_30_days = today + timedelta(days=30)

    if tenant_id:
        upcoming_milestones = Milestone.query.filter(
            Milestone.tenant_id == tenant_id,
            Milestone.end_date >= today,
            Milestone.end_date <= next_30_days,
            Milestone.status != 'Concluído'
        ).order_by(Milestone.end_date).limit(5).all()
    else:
        upcoming_milestones = Milestone.query.filter(
            Milestone.end_date >= today,
            Milestone.end_date <= next_30_days,
            Milestone.status != 'Concluído'
        ).order_by(Milestone.end_date).limit(5).all()

    # Get recent public calls
    recent_calls = PublicCall.query.filter(
        db.or_(
            PublicCall.tenant_id == None,
            PublicCall.tenant_id == tenant_id
        ),
        PublicCall.status == 'Aberta'
    ).order_by(PublicCall.updated_at.desc()).limit(6).all()

    # Get projects ending soon
    projects_ending_soon = []
    for p in projects:
        if p.end_date and p.end_date >= today and p.end_date <= next_30_days:
            projects_ending_soon.append(p)

    return render_template('home/dashboard.html',
                           tenant=tenant,
                           total_projects=total_projects,
                           active_projects=active_projects,
                           total_budget=total_budget,
                           total_expenses=total_expenses,
                           upcoming_milestones=upcoming_milestones,
                           recent_calls=recent_calls,
                           projects_ending_soon=projects_ending_soon,
                           ai_configured=bool(os.environ.get('ANTHROPIC_API_KEY')))


@home_bp.route('/home/insights', methods=['POST'])
@login_required
@tenant_required
def generate_insights():
    """Generate AI insights for the company's R&D sector."""
    client = get_anthropic_client()
    if not client:
        return jsonify({'error': 'API de IA não configurada'}), 400

    tenant = current_user.tenant
    tenant_id = get_current_tenant_id()

    # Gather company data
    if tenant_id:
        projects = Project.query.filter_by(tenant_id=tenant_id).all()
        total_budget = sum(p.budget or 0 for p in projects)
        categories = list(set(p.category for p in projects if p.category))
        funding_sources = list(set(p.funding_source for p in projects if p.funding_source))
    else:
        projects = Project.query.all()
        total_budget = sum(p.budget or 0 for p in projects)
        categories = list(set(p.category for p in projects if p.category))
        funding_sources = list(set(p.funding_source for p in projects if p.funding_source))

    # Get open calls
    open_calls = PublicCall.query.filter_by(status='Aberta').limit(10).all()
    calls_info = [f"- {c.source}: {c.title}" for c in open_calls]

    company_name = tenant.name if tenant else "Empresa"

    prompt = f"""Você é um consultor de inovação e P&D. Gere insights estratégicos para a empresa "{company_name}" baseado nos dados:

DADOS DA EMPRESA:
- Total de projetos: {len(projects)}
- Orçamento total em P&D: R$ {total_budget:,.2f}
- Áreas de atuação: {', '.join(categories) if categories else 'Não definidas'}
- Fontes de financiamento atuais: {', '.join(funding_sources) if funding_sources else 'Não definidas'}

CHAMADAS PÚBLICAS ABERTAS:
{chr(10).join(calls_info) if calls_info else 'Nenhuma chamada recente'}

Gere um JSON com:
{{
    "resumo_setor": "Análise breve do setor de P&D da empresa (2-3 frases)",
    "tendencias": ["Lista de 3-4 tendências relevantes para o setor"],
    "oportunidades": ["Lista de 2-3 oportunidades de financiamento ou parcerias"],
    "recomendacoes": ["Lista de 2-3 recomendações estratégicas"],
    "alertas": ["Lista de 1-2 pontos de atenção, se houver"]
}}

Seja específico e prático nas recomendações.
"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = response.content[0].text

        # Extract JSON
        import json
        start = response_text.find('{')
        end = response_text.rfind('}') + 1
        if start != -1 and end > start:
            insights = json.loads(response_text[start:end])
            return jsonify(insights)

        return jsonify({'error': 'Erro ao processar resposta'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500
