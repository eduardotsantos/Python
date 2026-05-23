"""
Portfolio routes - consolidated view of all company projects.
"""
from flask import Blueprint, render_template, request, Response
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from sqlalchemy import func

from models import db, Project, Program, Expense, Milestone, Resource, Timesheet, PublicCall
from services.tenant_utils import tenant_required, get_current_tenant_id

portfolio_bp = Blueprint('portfolio', __name__)


@portfolio_bp.route('/portfolio')
@login_required
@tenant_required
def dashboard():
    """Portfolio dashboard with consolidated data."""
    tenant_id = get_current_tenant_id()
    tenant = current_user.tenant

    # Get all projects
    projects = Project.query.filter_by(tenant_id=tenant_id).all()
    active_projects = [p for p in projects if p.status in ['Em Andamento', 'Planejamento']]

    # Budget and expenses
    total_budget = sum(p.budget or 0 for p in projects)
    total_spent = db.session.query(func.sum(Expense.amount)).filter_by(tenant_id=tenant_id).scalar() or 0

    # Expenses by category
    expenses_by_category = db.session.query(
        Expense.category,
        func.sum(Expense.amount)
    ).filter_by(tenant_id=tenant_id).group_by(Expense.category).all()

    # Expenses by project
    expenses_by_project = db.session.query(
        Project.code,
        Project.title,
        func.sum(Expense.amount)
    ).join(Expense, Project.id == Expense.project_id).filter(
        Project.tenant_id == tenant_id
    ).group_by(Project.id).all()

    # Projects by status
    projects_by_status = {}
    for p in projects:
        projects_by_status[p.status] = projects_by_status.get(p.status, 0) + 1

    # All milestones for Gantt
    milestones = Milestone.query.filter_by(tenant_id=tenant_id).order_by(Milestone.end_date).all()

    # Milestones with project info for Gantt
    gantt_data = []
    for m in milestones:
        project = Project.query.get(m.project_id)
        if project:
            gantt_data.append({
                'id': m.id,
                'name': m.title,
                'project_code': project.code,
                'project_title': project.title,
                'start': m.start_date.isoformat() if m.start_date else None,
                'end': m.end_date.isoformat() if m.end_date else None,
                'progress': m.progress or 0,
                'status': m.status
            })

    # Programs summary
    programs = Program.query.filter_by(tenant_id=tenant_id).all()

    # Total hours
    total_hours = db.session.query(func.sum(Timesheet.hours)).filter_by(tenant_id=tenant_id).scalar() or 0

    # Team size
    total_resources = Resource.query.filter_by(
        tenant_id=tenant_id,
        type='Pessoa',
        status='Ativo'
    ).count()

    # Calculate overall progress
    all_milestones = Milestone.query.filter_by(tenant_id=tenant_id).all()
    overall_progress = sum(m.progress or 0 for m in all_milestones) / len(all_milestones) if all_milestones else 0

    # Delayed milestones
    today = date.today()
    delayed_milestones = [m for m in all_milestones if m.end_date and m.end_date < today and m.status != 'Concluido']

    return render_template('portfolio/dashboard.html',
        tenant=tenant,
        total_projects=len(projects),
        active_projects=len(active_projects),
        total_budget=total_budget,
        total_spent=total_spent,
        remaining_budget=total_budget - total_spent,
        budget_percent=round((total_spent / total_budget * 100) if total_budget > 0 else 0, 1),
        expenses_by_category=expenses_by_category,
        expenses_by_project=expenses_by_project,
        projects_by_status=projects_by_status,
        gantt_data=gantt_data,
        programs=programs,
        total_hours=total_hours,
        total_resources=total_resources,
        overall_progress=round(overall_progress, 1),
        delayed_count=len(delayed_milestones),
        projects=projects
    )


@portfolio_bp.route('/portfolio/status-report')
@login_required
@tenant_required
def status_report():
    """Consolidated portfolio status report."""
    tenant_id = get_current_tenant_id()
    tenant = current_user.tenant

    projects = Project.query.filter_by(tenant_id=tenant_id).all()
    active_projects = [p for p in projects if p.status in ['Em Andamento', 'Planejamento']]

    # Budget
    total_budget = sum(p.budget or 0 for p in projects)
    total_spent = db.session.query(func.sum(Expense.amount)).filter_by(tenant_id=tenant_id).scalar() or 0

    # Schedule
    all_milestones = Milestone.query.filter_by(tenant_id=tenant_id).all()
    today = date.today()

    completed = len([m for m in all_milestones if m.status == 'Concluido'])
    delayed = len([m for m in all_milestones if m.end_date and m.end_date < today and m.status != 'Concluido'])
    on_track = len(all_milestones) - completed - delayed
    total_progress = sum(m.progress or 0 for m in all_milestones) / len(all_milestones) if all_milestones else 0

    schedule_status = {
        'status': 'red' if delayed > 0 else 'green',
        'label': 'Atrasado' if delayed > 0 else 'No prazo',
        'total': len(all_milestones),
        'completed': completed,
        'delayed': delayed,
        'on_track': on_track,
        'progress': round(total_progress, 1)
    }

    percent_used = (total_spent / total_budget * 100) if total_budget > 0 else 0
    cost_status = {
        'status': 'red' if percent_used > 100 else 'yellow' if percent_used > 85 else 'green',
        'label': 'Estourado' if percent_used > 100 else 'Atencao' if percent_used > 85 else 'Saudavel',
        'budget': total_budget,
        'spent': total_spent,
        'remaining': total_budget - total_spent,
        'percent_used': round(percent_used, 1)
    }

    # Risks
    risks = []
    if delayed > 0:
        risks.append({
            'type': 'schedule',
            'severity': 'high',
            'title': f'{delayed} marco(s) atrasado(s) no portfolio',
            'description': 'Existem marcos com data de entrega ultrapassada',
            'action': 'Revisar cronogramas dos projetos criticos'
        })
    if percent_used > 100:
        risks.append({
            'type': 'cost',
            'severity': 'high',
            'title': 'Orcamento do portfolio estourado',
            'description': f'Gasto excede orcamento em R$ {total_spent - total_budget:,.2f}',
            'action': 'Revisar alocacao de recursos entre projetos'
        })

    # Projects ending soon
    next_30_days = today + timedelta(days=30)
    projects_ending = [p for p in active_projects if p.end_date and p.end_date <= next_30_days]
    if projects_ending:
        risks.append({
            'type': 'schedule',
            'severity': 'medium',
            'title': f'{len(projects_ending)} projeto(s) encerrando em 30 dias',
            'description': ', '.join([p.code for p in projects_ending[:3]]),
            'action': 'Preparar entregas finais e documentacao'
        })

    # Overall health
    if any(r['severity'] == 'high' for r in risks):
        overall_health = 'red'
        overall_label = 'Critico'
    elif any(r['severity'] == 'medium' for r in risks):
        overall_health = 'yellow'
        overall_label = 'Atencao'
    else:
        overall_health = 'green'
        overall_label = 'Saudavel'

    # Hours and team
    total_hours = db.session.query(func.sum(Timesheet.hours)).filter_by(tenant_id=tenant_id).scalar() or 0

    team = Resource.query.filter_by(
        tenant_id=tenant_id,
        type='Pessoa',
        status='Ativo'
    ).all()
    unique_team = {r.name: r for r in team}.values()

    # Upcoming milestones
    upcoming_milestones = Milestone.query.filter_by(tenant_id=tenant_id).filter(
        Milestone.status != 'Concluido',
        Milestone.end_date >= today
    ).order_by(Milestone.end_date).limit(10).all()

    # Projects summary for the report
    projects_summary = []
    for p in active_projects[:10]:
        milestones = Milestone.query.filter_by(project_id=p.id).all()
        progress = sum(m.progress or 0 for m in milestones) / len(milestones) if milestones else 0
        spent = db.session.query(func.sum(Expense.amount)).filter_by(project_id=p.id).scalar() or 0
        projects_summary.append({
            'project': p,
            'progress': round(progress, 1),
            'budget_used': round((spent / p.budget * 100) if p.budget else 0, 1),
            'spent': spent
        })

    return render_template('portfolio/status_report.html',
        tenant=tenant,
        report_date=datetime.now(),
        total_projects=len(projects),
        active_projects=len(active_projects),
        schedule_status=schedule_status,
        cost_status=cost_status,
        risks=risks,
        overall_health=overall_health,
        overall_label=overall_label,
        total_hours=total_hours,
        team=list(unique_team),
        upcoming_milestones=upcoming_milestones,
        projects_summary=projects_summary
    )


@portfolio_bp.route('/portfolio/export-project')
@login_required
@tenant_required
def export_portfolio_to_project():
    """Export entire portfolio to MS Project XML."""
    tenant_id = get_current_tenant_id()

    from services.msproject_service import export_portfolio_to_xml
    xml_content = export_portfolio_to_xml(tenant_id)

    response = Response(
        xml_content,
        mimetype='application/xml',
        headers={'Content-Disposition': 'attachment; filename=portfolio.xml'}
    )
    return response


@portfolio_bp.route('/portfolio/analytics')
@login_required
@tenant_required
def analytics():
    """Portfolio analytics and charts data."""
    tenant_id = get_current_tenant_id()

    # Expenses by month
    expenses_by_month = db.session.query(
        func.strftime('%Y-%m', Expense.date),
        func.sum(Expense.amount)
    ).filter_by(tenant_id=tenant_id).group_by(
        func.strftime('%Y-%m', Expense.date)
    ).order_by(func.strftime('%Y-%m', Expense.date)).all()

    # Budget vs Spent by project
    projects = Project.query.filter_by(tenant_id=tenant_id).all()
    budget_vs_spent = []
    for p in projects:
        spent = db.session.query(func.sum(Expense.amount)).filter_by(project_id=p.id).scalar() or 0
        budget_vs_spent.append({
            'code': p.code,
            'title': p.title,
            'budget': p.budget or 0,
            'spent': spent
        })

    return render_template('portfolio/analytics.html',
        expenses_by_month=expenses_by_month,
        budget_vs_spent=budget_vs_spent
    )
