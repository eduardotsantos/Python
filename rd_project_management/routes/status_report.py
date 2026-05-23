"""
Status Report routes for project tracking in meetings.
Provides one-page status report with schedule, costs, and risks.
"""
from flask import Blueprint, render_template, request, make_response
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from sqlalchemy import func

from models import db, Project, Expense, Milestone, Resource, Timesheet
from services.tenant_utils import tenant_required, ensure_tenant_access, get_current_tenant_id

status_report_bp = Blueprint('status_report', __name__)


def calculate_schedule_status(project):
    """Calculate schedule status based on milestones."""
    milestones = Milestone.query.filter_by(project_id=project.id).all()

    if not milestones:
        return {
            'status': 'gray',
            'label': 'Sem marcos',
            'total': 0,
            'completed': 0,
            'delayed': 0,
            'on_track': 0,
            'progress': 0
        }

    today = date.today()
    completed = 0
    delayed = 0
    on_track = 0
    total_progress = 0

    for m in milestones:
        total_progress += m.progress or 0
        if m.status == 'Concluído':
            completed += 1
        elif m.end_date and m.end_date < today and m.status != 'Concluído':
            delayed += 1
        else:
            on_track += 1

    avg_progress = total_progress / len(milestones) if milestones else 0

    if delayed > 0:
        status = 'red'
        label = 'Atrasado'
    elif completed == len(milestones):
        status = 'green'
        label = 'Concluído'
    else:
        status = 'green'
        label = 'No prazo'

    return {
        'status': status,
        'label': label,
        'total': len(milestones),
        'completed': completed,
        'delayed': delayed,
        'on_track': on_track,
        'progress': round(avg_progress, 1)
    }


def calculate_cost_status(project):
    """Calculate cost/budget status."""
    budget = project.budget or 0
    expenses = Expense.query.filter_by(project_id=project.id).all()
    total_spent = sum(e.amount or 0 for e in expenses)

    if budget == 0:
        return {
            'status': 'gray',
            'label': 'Sem orçamento',
            'budget': 0,
            'spent': total_spent,
            'remaining': 0,
            'percent_used': 0,
            'by_category': {}
        }

    percent_used = (total_spent / budget) * 100 if budget > 0 else 0
    remaining = budget - total_spent

    # Group by category
    by_category = {}
    for e in expenses:
        cat = e.category or 'Outros'
        by_category[cat] = by_category.get(cat, 0) + (e.amount or 0)

    if percent_used > 100:
        status = 'red'
        label = 'Estourado'
    elif percent_used > 85:
        status = 'yellow'
        label = 'Atenção'
    else:
        status = 'green'
        label = 'Saudável'

    return {
        'status': status,
        'label': label,
        'budget': budget,
        'spent': total_spent,
        'remaining': remaining,
        'percent_used': round(percent_used, 1),
        'by_category': by_category
    }


def calculate_evm_metrics(project, schedule_status, cost_status):
    """Calculate Earned Value Management metrics (ETC, EAC, CPI, SPI, etc.)."""
    bac = cost_status['budget']  # Budget at Completion
    ac = cost_status['spent']     # Actual Cost
    progress = schedule_status['progress'] / 100 if schedule_status['progress'] > 0 else 0

    # If no budget, return empty metrics
    if bac == 0:
        return {
            'bac': 0,
            'ac': ac,
            'ev': 0,
            'pv': 0,
            'cpi': 0,
            'spi': 0,
            'cv': 0,
            'sv': 0,
            'etc': 0,
            'eac': ac,
            'vac': 0,
            'tcpi': 0,
            'status': 'gray',
            'has_data': False
        }

    # Earned Value = BAC × Progress %
    ev = bac * progress

    # Planned Value - based on time elapsed
    pv = 0
    time_elapsed_pct = 0
    if project.start_date and project.end_date:
        total_days = (project.end_date - project.start_date).days
        if total_days > 0:
            days_elapsed = (date.today() - project.start_date).days
            time_elapsed_pct = min(max(days_elapsed / total_days, 0), 1)
            pv = bac * time_elapsed_pct

    # Cost Performance Index (CPI) = EV / AC
    cpi = ev / ac if ac > 0 else (1.0 if ev == 0 else float('inf'))

    # Schedule Performance Index (SPI) = EV / PV
    spi = ev / pv if pv > 0 else (1.0 if ev == 0 else float('inf'))

    # Cost Variance (CV) = EV - AC
    cv = ev - ac

    # Schedule Variance (SV) = EV - PV
    sv = ev - pv

    # Estimate to Complete (ETC)
    if cpi > 0 and cpi != float('inf'):
        etc = (bac - ev) / cpi
    else:
        etc = bac - ev

    # Estimate at Completion (EAC) = AC + ETC
    eac = ac + etc

    # Variance at Completion (VAC) = BAC - EAC
    vac = bac - eac

    # To Complete Performance Index (TCPI) = (BAC - EV) / (BAC - AC)
    tcpi = (bac - ev) / (bac - ac) if (bac - ac) > 0 else float('inf')

    # Determine status
    if cpi >= 1.0 and spi >= 1.0:
        status = 'green'
    elif cpi >= 0.9 and spi >= 0.9:
        status = 'yellow'
    else:
        status = 'red'

    return {
        'bac': round(bac, 2),
        'ac': round(ac, 2),
        'ev': round(ev, 2),
        'pv': round(pv, 2),
        'cpi': round(cpi, 2) if cpi != float('inf') else 0,
        'spi': round(spi, 2) if spi != float('inf') else 0,
        'cv': round(cv, 2),
        'sv': round(sv, 2),
        'etc': round(etc, 2),
        'eac': round(eac, 2),
        'vac': round(vac, 2),
        'tcpi': round(tcpi, 2) if tcpi != float('inf') else 0,
        'time_elapsed_pct': round(time_elapsed_pct * 100, 1),
        'status': status,
        'has_data': True
    }


def identify_risks(project, schedule_status, cost_status):
    """Identify project risks based on current status."""
    risks = []

    # Schedule risks
    if schedule_status['delayed'] > 0:
        risks.append({
            'type': 'schedule',
            'severity': 'high',
            'title': f"{schedule_status['delayed']} marco(s) atrasado(s)",
            'description': 'Existem marcos com data de entrega ultrapassada',
            'action': 'Revisar cronograma e realocar recursos'
        })

    # Check if project is ending soon
    if project.end_date:
        days_remaining = (project.end_date - date.today()).days
        if days_remaining < 0:
            risks.append({
                'type': 'schedule',
                'severity': 'high',
                'title': 'Projeto expirado',
                'description': f'Data de término foi há {abs(days_remaining)} dias',
                'action': 'Solicitar prorrogação ou encerrar projeto'
            })
        elif days_remaining <= 30:
            risks.append({
                'type': 'schedule',
                'severity': 'medium',
                'title': f'Projeto termina em {days_remaining} dias',
                'description': 'Prazo de encerramento próximo',
                'action': 'Acelerar entregas finais'
            })

    # Budget risks
    if cost_status['percent_used'] > 100:
        overspent = cost_status['spent'] - cost_status['budget']
        risks.append({
            'type': 'cost',
            'severity': 'high',
            'title': 'Orçamento estourado',
            'description': f'Gasto excede orçamento em R$ {overspent:,.2f}',
            'action': 'Solicitar remanejamento ou aditivo'
        })
    elif cost_status['percent_used'] > 85:
        risks.append({
            'type': 'cost',
            'severity': 'medium',
            'title': 'Orçamento crítico',
            'description': f'{cost_status["percent_used"]:.1f}% do orçamento já utilizado',
            'action': 'Controlar gastos e priorizar despesas essenciais'
        })

    # Progress risk
    if schedule_status['progress'] < 30 and project.start_date:
        days_elapsed = (date.today() - project.start_date).days
        if project.end_date:
            total_days = (project.end_date - project.start_date).days
            if total_days > 0:
                time_elapsed_pct = (days_elapsed / total_days) * 100
                if time_elapsed_pct > 50 and schedule_status['progress'] < 30:
                    risks.append({
                        'type': 'execution',
                        'severity': 'high',
                        'title': 'Progresso abaixo do esperado',
                        'description': f'{time_elapsed_pct:.0f}% do tempo decorrido, apenas {schedule_status["progress"]:.0f}% concluído',
                        'action': 'Revisar escopo ou aumentar equipe'
                    })

    # Resource risk - check if has resources allocated
    resources = Resource.query.filter_by(project_id=project.id, status='Ativo').count()
    if resources == 0:
        risks.append({
            'type': 'resource',
            'severity': 'medium',
            'title': 'Sem recursos alocados',
            'description': 'Nenhum recurso ativo no projeto',
            'action': 'Alocar equipe para execução'
        })

    # Sort by severity
    severity_order = {'high': 0, 'medium': 1, 'low': 2}
    risks.sort(key=lambda x: severity_order.get(x['severity'], 3))

    return risks


def get_recent_activities(project, limit=5):
    """Get recent activities from timesheet."""
    entries = Timesheet.query.filter_by(project_id=project.id)\
        .order_by(Timesheet.date.desc())\
        .limit(limit).all()

    return [{
        'date': e.date,
        'user': e.user.full_name if e.user else 'N/A',
        'activity': e.activity,
        'hours': e.hours
    } for e in entries]


def get_upcoming_milestones(project, limit=5):
    """Get upcoming milestones."""
    today = date.today()
    milestones = Milestone.query.filter(
        Milestone.project_id == project.id,
        Milestone.status != 'Concluído',
        Milestone.end_date >= today
    ).order_by(Milestone.end_date).limit(limit).all()

    return milestones


@status_report_bp.route('/projects/<int:project_id>/status-report')
@login_required
@tenant_required
def view_report(project_id):
    """View one-page status report for a project."""
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    tenant = current_user.tenant

    # Calculate statuses
    schedule_status = calculate_schedule_status(project)
    cost_status = calculate_cost_status(project)
    evm_metrics = calculate_evm_metrics(project, schedule_status, cost_status)
    risks = identify_risks(project, schedule_status, cost_status)

    # Get additional data
    recent_activities = get_recent_activities(project)
    upcoming_milestones = get_upcoming_milestones(project)

    # Calculate overall health
    if any(r['severity'] == 'high' for r in risks):
        overall_health = 'red'
        overall_label = 'Crítico'
    elif any(r['severity'] == 'medium' for r in risks):
        overall_health = 'yellow'
        overall_label = 'Atenção'
    elif schedule_status['status'] == 'gray' and cost_status['status'] == 'gray':
        overall_health = 'gray'
        overall_label = 'Sem dados'
    else:
        overall_health = 'green'
        overall_label = 'Saudável'

    # Get team
    team = Resource.query.filter_by(project_id=project_id, type='Pessoa', status='Ativo').all()

    # Total hours
    total_hours = db.session.query(func.sum(Timesheet.hours))\
        .filter_by(project_id=project_id).scalar() or 0

    return render_template('status_report/report.html',
        project=project,
        tenant=tenant,
        report_date=datetime.now(),
        schedule_status=schedule_status,
        cost_status=cost_status,
        evm_metrics=evm_metrics,
        risks=risks,
        overall_health=overall_health,
        overall_label=overall_label,
        recent_activities=recent_activities,
        upcoming_milestones=upcoming_milestones,
        team=team,
        total_hours=total_hours
    )


@status_report_bp.route('/projects/<int:project_id>/status-report/print')
@login_required
@tenant_required
def print_report(project_id):
    """Print-friendly version of status report."""
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    tenant = current_user.tenant

    # Calculate statuses
    schedule_status = calculate_schedule_status(project)
    cost_status = calculate_cost_status(project)
    evm_metrics = calculate_evm_metrics(project, schedule_status, cost_status)
    risks = identify_risks(project, schedule_status, cost_status)

    # Get additional data
    recent_activities = get_recent_activities(project)
    upcoming_milestones = get_upcoming_milestones(project)

    # Calculate overall health
    if any(r['severity'] == 'high' for r in risks):
        overall_health = 'red'
        overall_label = 'Crítico'
    elif any(r['severity'] == 'medium' for r in risks):
        overall_health = 'yellow'
        overall_label = 'Atenção'
    else:
        overall_health = 'green'
        overall_label = 'Saudável'

    team = Resource.query.filter_by(project_id=project_id, type='Pessoa', status='Ativo').all()
    total_hours = db.session.query(func.sum(Timesheet.hours))\
        .filter_by(project_id=project_id).scalar() or 0

    return render_template('status_report/print.html',
        project=project,
        tenant=tenant,
        report_date=datetime.now(),
        schedule_status=schedule_status,
        cost_status=cost_status,
        evm_metrics=evm_metrics,
        risks=risks,
        overall_health=overall_health,
        overall_label=overall_label,
        recent_activities=recent_activities,
        upcoming_milestones=upcoming_milestones,
        team=team,
        total_hours=total_hours
    )
