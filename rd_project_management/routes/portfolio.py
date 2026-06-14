"""
Portfolio routes - consolidated view of all company projects.
"""
from flask import Blueprint, render_template, request, Response
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from sqlalchemy import func

from models import db, Project, Program, Expense, Milestone, Resource, Timesheet, PublicCall, Risk, PendingItem, NonConformity, Bug, CorrectiveAction
from services.tenant_utils import tenant_required, get_current_tenant_id

portfolio_bp = Blueprint('portfolio', __name__)


@portfolio_bp.route('/portfolio')
@login_required
@tenant_required
def dashboard():
    """Portfolio dashboard with consolidated data."""
    tenant_id = get_current_tenant_id()
    tenant = current_user.tenant

    # Get all projects (superadmin sees all)
    if tenant_id:
        projects = Project.query.filter_by(tenant_id=tenant_id).all()
    else:
        projects = Project.query.all()

    active_projects = [p for p in projects if p.status in ['Em Andamento', 'Planejamento']]

    # Budget and expenses
    total_budget = sum(p.budget or 0 for p in projects)

    if tenant_id:
        total_spent = db.session.query(func.sum(Expense.amount)).filter_by(tenant_id=tenant_id).scalar() or 0
    else:
        total_spent = db.session.query(func.sum(Expense.amount)).scalar() or 0

    # Expenses by category
    if tenant_id:
        expenses_by_category = db.session.query(
            Expense.category,
            func.sum(Expense.amount)
        ).filter_by(tenant_id=tenant_id).group_by(Expense.category).all()
    else:
        expenses_by_category = db.session.query(
            Expense.category,
            func.sum(Expense.amount)
        ).group_by(Expense.category).all()

    # Expenses by project
    if tenant_id:
        expenses_by_project = db.session.query(
            Project.code,
            Project.title,
            func.sum(Expense.amount)
        ).join(Expense, Project.id == Expense.project_id).filter(
            Project.tenant_id == tenant_id
        ).group_by(Project.id).all()
    else:
        expenses_by_project = db.session.query(
            Project.code,
            Project.title,
            func.sum(Expense.amount)
        ).join(Expense, Project.id == Expense.project_id).group_by(Project.id).all()

    # Projects by status
    projects_by_status = {}
    for p in projects:
        projects_by_status[p.status] = projects_by_status.get(p.status, 0) + 1

    # All milestones for Gantt
    if tenant_id:
        milestones = Milestone.query.filter_by(tenant_id=tenant_id).order_by(Milestone.end_date).all()
    else:
        milestones = Milestone.query.order_by(Milestone.end_date).all()

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
    if tenant_id:
        programs = Program.query.filter_by(tenant_id=tenant_id).all()
    else:
        programs = Program.query.all()

    # Total hours
    if tenant_id:
        total_hours = db.session.query(func.sum(Timesheet.hours)).filter_by(tenant_id=tenant_id).scalar() or 0
    else:
        total_hours = db.session.query(func.sum(Timesheet.hours)).scalar() or 0

    # Team size
    if tenant_id:
        total_resources = Resource.query.filter_by(
            tenant_id=tenant_id,
            type='Pessoa',
            status='Ativo'
        ).count()
    else:
        total_resources = Resource.query.filter_by(
            type='Pessoa',
            status='Ativo'
        ).count()

    # Calculate overall progress
    all_milestones = milestones  # Reuse from above
    overall_progress = sum(m.progress or 0 for m in all_milestones) / len(all_milestones) if all_milestones else 0

    # Delayed milestones
    today = date.today()
    delayed_milestones = [m for m in all_milestones if m.end_date and m.end_date < today and m.status != 'Concluido']

    # TRL Distribution
    trl_distribution = {}
    for p in projects:
        trl = p.trl or 1
        trl_distribution[trl] = trl_distribution.get(trl, 0) + 1

    # Innovation Type Distribution
    innovation_type_distribution = {}
    for p in projects:
        itype = p.innovation_type or 'Não definido'
        innovation_type_distribution[itype] = innovation_type_distribution.get(itype, 0) + 1

    # Innovation Scope Distribution
    innovation_scope_distribution = {}
    for p in projects:
        scope = p.innovation_scope or 'Não definido'
        innovation_scope_distribution[scope] = innovation_scope_distribution.get(scope, 0) + 1

    # Average TRL
    trls = [p.trl or 1 for p in projects]
    avg_trl = sum(trls) / len(trls) if trls else 1

    # Projects by TRL level for detailed view
    projects_by_trl = {}
    for p in projects:
        trl = p.trl or 1
        if trl not in projects_by_trl:
            projects_by_trl[trl] = []
        projects_by_trl[trl].append({
            'code': p.code,
            'title': p.title,
            'status': p.status
        })

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
        projects=projects,
        trl_distribution=trl_distribution,
        innovation_type_distribution=innovation_type_distribution,
        innovation_scope_distribution=innovation_scope_distribution,
        avg_trl=round(avg_trl, 1),
        projects_by_trl=projects_by_trl
    )


@portfolio_bp.route('/portfolio/status-report')
@login_required
@tenant_required
def status_report():
    """Consolidated portfolio status report."""
    tenant_id = get_current_tenant_id()
    tenant = current_user.tenant

    # Get all projects (superadmin sees all)
    if tenant_id:
        projects = Project.query.filter_by(tenant_id=tenant_id).all()
    else:
        projects = Project.query.all()

    active_projects = [p for p in projects if p.status in ['Em Andamento', 'Planejamento']]

    # Budget
    total_budget = sum(p.budget or 0 for p in projects)
    if tenant_id:
        total_spent = db.session.query(func.sum(Expense.amount)).filter_by(tenant_id=tenant_id).scalar() or 0
    else:
        total_spent = db.session.query(func.sum(Expense.amount)).scalar() or 0

    # Schedule
    if tenant_id:
        all_milestones = Milestone.query.filter_by(tenant_id=tenant_id).all()
    else:
        all_milestones = Milestone.query.all()

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
    if tenant_id:
        total_hours = db.session.query(func.sum(Timesheet.hours)).filter_by(tenant_id=tenant_id).scalar() or 0
        team = Resource.query.filter_by(tenant_id=tenant_id, type='Pessoa', status='Ativo').all()
        upcoming_milestones = Milestone.query.filter_by(tenant_id=tenant_id).filter(
            Milestone.status != 'Concluido',
            Milestone.end_date >= today
        ).order_by(Milestone.end_date).limit(10).all()
    else:
        total_hours = db.session.query(func.sum(Timesheet.hours)).scalar() or 0
        team = Resource.query.filter_by(type='Pessoa', status='Ativo').all()
        upcoming_milestones = Milestone.query.filter(
            Milestone.status != 'Concluido',
            Milestone.end_date >= today
        ).order_by(Milestone.end_date).limit(10).all()

    unique_team = {r.name: r for r in team}.values()

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

    # Compliance status for entire portfolio
    project_ids = [p.id for p in projects]

    all_risks_compliance = Risk.query.filter(Risk.project_id.in_(project_ids)).all() if project_ids else []
    open_risks = [r for r in all_risks_compliance if r.status not in ['Fechado', 'Mitigado', 'Encerrado']]
    critical_risks = [r for r in open_risks if r.probability >= 4 and r.impact >= 4]

    all_pending = PendingItem.query.filter(PendingItem.project_id.in_(project_ids)).all() if project_ids else []
    open_pending = [p for p in all_pending if p.status not in ['Concluída', 'Fechada', 'Resolvida']]
    overdue_pending = [p for p in open_pending if p.due_date and p.due_date < today]

    all_bugs = Bug.query.filter(Bug.project_id.in_(project_ids)).all() if project_ids else []
    open_bugs = [b for b in all_bugs if b.status not in ['Fechado', 'Resolvido', 'Encerrado']]
    critical_bugs = [b for b in open_bugs if b.severity in ['Crítico', 'Crítica', 'Critical']]

    all_ncs = NonConformity.query.filter(NonConformity.project_id.in_(project_ids)).all() if project_ids else []
    open_ncs = [nc for nc in all_ncs if nc.status not in ['Fechada', 'Encerrada', 'Resolvida']]

    all_actions = CorrectiveAction.query.filter(CorrectiveAction.project_id.in_(project_ids)).all() if project_ids else []
    pending_actions = [a for a in all_actions if a.status not in ['Concluída', 'Implementada', 'Fechada']]

    # Determine compliance status
    if critical_risks or critical_bugs or len(overdue_pending) > 3:
        compliance_color = 'red'
        compliance_label = 'Crítico'
    elif open_risks or overdue_pending or open_ncs:
        compliance_color = 'yellow'
        compliance_label = 'Atenção'
    else:
        compliance_color = 'green'
        compliance_label = 'Conforme'

    compliance_status = {
        'status': compliance_color,
        'label': compliance_label,
        'open_risks': len(open_risks),
        'critical_risks': len(critical_risks),
        'open_pending': len(open_pending),
        'overdue_pending': len(overdue_pending),
        'overdue_items': overdue_pending[:10],
        'open_bugs': len(open_bugs),
        'critical_bugs': len(critical_bugs),
        'open_ncs': len(open_ncs),
        'pending_actions': len(pending_actions),
        'has_issues': len(open_risks) + len(overdue_pending) + len(open_bugs) + len(open_ncs) > 0
    }

    # Update overall health to include compliance
    if compliance_status['status'] == 'red':
        overall_health = 'red'
        overall_label = 'Critico'

    # PMBOK 8 - Value Delivery calculation
    total_expected_value = sum(getattr(p, 'expected_value', 0) or 0 for p in projects)
    total_realized_value = sum(getattr(p, 'realized_value', 0) or 0 for p in projects)
    projects_with_value = len([p for p in projects if getattr(p, 'expected_value', 0) and p.expected_value > 0])
    value_capture_percent = (total_realized_value / total_expected_value * 100) if total_expected_value > 0 else 0

    value_status = {
        'total_expected': total_expected_value,
        'total_realized': total_realized_value,
        'capture_percent': round(value_capture_percent, 1),
        'projects_with_value': projects_with_value
    }

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
        projects_summary=projects_summary,
        compliance_status=compliance_status,
        value_status=value_status
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
    if tenant_id:
        expenses_by_month = db.session.query(
            func.strftime('%Y-%m', Expense.date),
            func.sum(Expense.amount)
        ).filter_by(tenant_id=tenant_id).group_by(
            func.strftime('%Y-%m', Expense.date)
        ).order_by(func.strftime('%Y-%m', Expense.date)).all()
        projects = Project.query.filter_by(tenant_id=tenant_id).all()
    else:
        expenses_by_month = db.session.query(
            func.strftime('%Y-%m', Expense.date),
            func.sum(Expense.amount)
        ).group_by(
            func.strftime('%Y-%m', Expense.date)
        ).order_by(func.strftime('%Y-%m', Expense.date)).all()
        projects = Project.query.all()

    # Budget vs Spent by project
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
