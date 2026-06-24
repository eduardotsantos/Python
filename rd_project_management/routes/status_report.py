"""
Status Report routes for project tracking in meetings.
Provides one-page status report with schedule, costs, and risks.
"""
from flask import Blueprint, render_template, request, make_response
from flask_login import login_required, current_user
from flask_babel import _
from datetime import datetime, date, timedelta
from sqlalchemy import func

from models import db, Project, Expense, Milestone, Resource, Timesheet, Risk, PendingItem, NonConformity, Bug, CorrectiveAction
from services.tenant_utils import tenant_required, ensure_tenant_access, get_current_tenant_id

status_report_bp = Blueprint('status_report', __name__)


def calculate_schedule_status(project):
    """Calculate schedule status based on milestones."""
    milestones = Milestone.query.filter_by(project_id=project.id).all()

    if not milestones:
        return {
            'status': 'gray',
            'label': _('Sem marcos'),
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
        label = _('Atrasado')
    elif completed == len(milestones):
        status = 'green'
        label = _('Concluido')
    else:
        status = 'green'
        label = _('No prazo')

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
            'label': _('Sem orcamento'),
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
        cat = e.category or _('Outros')
        by_category[cat] = by_category.get(cat, 0) + (e.amount or 0)

    if percent_used > 100:
        status = 'red'
        label = _('Estourado')
    elif percent_used > 85:
        status = 'yellow'
        label = _('Atencao')
    else:
        status = 'green'
        label = _('Saudavel')

    return {
        'status': status,
        'label': label,
        'budget': budget,
        'spent': total_spent,
        'remaining': remaining,
        'percent_used': round(percent_used, 1),
        'by_category': by_category
    }


def calculate_resource_cost_status(project):
    """Calculate resource costs: planned (allocated) vs realized (timesheet)."""
    resources = Resource.query.filter_by(project_id=project.id).all()
    timesheets = Timesheet.query.filter_by(project_id=project.id).all()

    # Build resource cost map
    resource_costs = {r.id: r.hourly_cost or 0 for r in resources}

    # Planned cost: hours_allocated × hourly_cost
    planned_cost = sum((r.hours_allocated or 0) * (r.hourly_cost or 0) for r in resources)
    planned_hours = sum(r.hours_allocated or 0 for r in resources)

    # Realized cost from timesheet
    realized_cost = 0
    realized_hours = 0
    cost_by_resource = {}
    hours_by_resource = {}

    for t in timesheets:
        hours = t.hours or 0
        realized_hours += hours

        # Get hourly cost from resource if linked
        if t.resource_id and t.resource_id in resource_costs:
            hourly = resource_costs[t.resource_id]
            cost = hours * hourly
            realized_cost += cost

            # Track by resource
            res = Resource.query.get(t.resource_id)
            if res:
                name = res.name
                cost_by_resource[name] = cost_by_resource.get(name, 0) + cost
                hours_by_resource[name] = hours_by_resource.get(name, 0) + hours

    # Calculate variance
    cost_variance = planned_cost - realized_cost
    hours_variance = planned_hours - realized_hours

    # Determine status
    if planned_cost > 0:
        cost_percent = (realized_cost / planned_cost) * 100
        if cost_percent > 100:
            status = 'red'
            label = _('Acima do planejado')
        elif cost_percent > 85:
            status = 'yellow'
            label = _('Atencao')
        else:
            status = 'green'
            label = _('Dentro do planejado')
    else:
        cost_percent = 0
        status = 'gray'
        label = _('Sem planejamento')

    return {
        'status': status,
        'label': label,
        'planned_cost': round(planned_cost, 2),
        'realized_cost': round(realized_cost, 2),
        'cost_variance': round(cost_variance, 2),
        'cost_percent': round(cost_percent, 1),
        'planned_hours': round(planned_hours, 1),
        'realized_hours': round(realized_hours, 1),
        'hours_variance': round(hours_variance, 1),
        'cost_by_resource': cost_by_resource,
        'hours_by_resource': hours_by_resource,
        'has_data': planned_cost > 0 or realized_cost > 0
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
            'title': _('%(count)d marco(s) atrasado(s)', count=schedule_status['delayed']),
            'description': _('Existem marcos com data de entrega ultrapassada'),
            'action': _('Revisar cronograma e realocar recursos')
        })

    # Check if project is ending soon
    if project.end_date:
        days_remaining = (project.end_date - date.today()).days
        if days_remaining < 0:
            risks.append({
                'type': 'schedule',
                'severity': 'high',
                'title': _('Projeto expirado'),
                'description': _('Data de termino foi ha %(days)d dias', days=abs(days_remaining)),
                'action': _('Solicitar prorrogacao ou encerrar projeto')
            })
        elif days_remaining <= 30:
            risks.append({
                'type': 'schedule',
                'severity': 'medium',
                'title': _('Projeto termina em %(days)d dias', days=days_remaining),
                'description': _('Prazo de encerramento proximo'),
                'action': _('Acelerar entregas finais')
            })

    # Budget risks
    if cost_status['percent_used'] > 100:
        overspent = cost_status['spent'] - cost_status['budget']
        risks.append({
            'type': 'cost',
            'severity': 'high',
            'title': _('Orcamento estourado'),
            'description': _('Gasto excede orcamento em R$ %(value).2f', value=overspent),
            'action': _('Solicitar remanejamento ou aditivo')
        })
    elif cost_status['percent_used'] > 85:
        risks.append({
            'type': 'cost',
            'severity': 'medium',
            'title': _('Orcamento critico'),
            'description': _('%(percent).1f%% do orcamento ja utilizado', percent=cost_status["percent_used"]),
            'action': _('Controlar gastos e priorizar despesas essenciais')
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
                        'title': _('Progresso abaixo do esperado'),
                        'description': _('%(time).0f%% do tempo decorrido, apenas %(progress).0f%% concluido', time=time_elapsed_pct, progress=schedule_status["progress"]),
                        'action': _('Revisar escopo ou aumentar equipe')
                    })

    # Resource risk - check if has resources allocated
    resources = Resource.query.filter_by(project_id=project.id, status='Ativo').count()
    if resources == 0:
        risks.append({
            'type': 'resource',
            'severity': 'medium',
            'title': _('Sem recursos alocados'),
            'description': _('Nenhum recurso ativo no projeto'),
            'action': _('Alocar equipe para execucao')
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


def get_compliance_status(project):
    """Get compliance items status (risks, pending, bugs, NCs, corrective actions)."""
    today = date.today()

    # Risks
    risks = Risk.query.filter_by(project_id=project.id).all()
    open_risks = [r for r in risks if r.status not in ['Fechado', 'Mitigado', 'Encerrado']]
    critical_risks = [r for r in open_risks if r.probability >= 4 and r.impact >= 4]

    # Pending Items
    pending = PendingItem.query.filter_by(project_id=project.id).all()
    open_pending = [p for p in pending if p.status not in ['Concluída', 'Fechada', 'Resolvida']]
    overdue_pending = [p for p in open_pending if p.due_date and p.due_date < today]

    # Bugs
    bugs = Bug.query.filter_by(project_id=project.id).all()
    open_bugs = [b for b in bugs if b.status not in ['Fechado', 'Resolvido', 'Encerrado']]
    critical_bugs = [b for b in open_bugs if b.severity in ['Crítico', 'Crítica', 'Critical']]

    # Non-Conformities
    ncs = NonConformity.query.filter_by(project_id=project.id).all()
    open_ncs = [nc for nc in ncs if nc.status not in ['Fechada', 'Encerrada', 'Resolvida']]

    # Corrective Actions
    actions = CorrectiveAction.query.filter_by(project_id=project.id).all()
    pending_actions = [a for a in actions if a.status not in ['Concluída', 'Implementada', 'Fechada']]

    # Determine overall compliance status
    if critical_risks or critical_bugs or len(overdue_pending) > 3:
        status = 'red'
        label = _('Critico')
    elif open_risks or overdue_pending or open_ncs:
        status = 'yellow'
        label = _('Atencao')
    else:
        status = 'green'
        label = _('Conforme')

    return {
        'status': status,
        'label': label,
        # Risks
        'total_risks': len(risks),
        'open_risks': len(open_risks),
        'critical_risks': len(critical_risks),
        'risks': open_risks[:5],
        # Pending
        'total_pending': len(pending),
        'open_pending': len(open_pending),
        'overdue_pending': len(overdue_pending),
        'overdue_items': overdue_pending[:10],
        'pending_items': open_pending[:5],
        # Bugs
        'total_bugs': len(bugs),
        'open_bugs': len(open_bugs),
        'critical_bugs': len(critical_bugs),
        'bugs': open_bugs[:5],
        # NCs
        'total_ncs': len(ncs),
        'open_ncs': len(open_ncs),
        'ncs': open_ncs[:5],
        # Actions
        'total_actions': len(actions),
        'pending_actions': len(pending_actions),
        'actions': pending_actions[:5],
        # Summary
        'has_issues': len(open_risks) + len(overdue_pending) + len(open_bugs) + len(open_ncs) > 0
    }


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
    resource_cost_status = calculate_resource_cost_status(project)
    evm_metrics = calculate_evm_metrics(project, schedule_status, cost_status)
    risks = identify_risks(project, schedule_status, cost_status)
    compliance_status = get_compliance_status(project)

    # Get additional data
    recent_activities = get_recent_activities(project)
    upcoming_milestones = get_upcoming_milestones(project)

    # Calculate overall health (include compliance status)
    if any(r['severity'] == 'high' for r in risks) or compliance_status['status'] == 'red':
        overall_health = 'red'
        overall_label = _('Critico')
    elif any(r['severity'] == 'medium' for r in risks) or compliance_status['status'] == 'yellow':
        overall_health = 'yellow'
        overall_label = _('Atencao')
    elif schedule_status['status'] == 'gray' and cost_status['status'] == 'gray':
        overall_health = 'gray'
        overall_label = _('Sem dados')
    else:
        overall_health = 'green'
        overall_label = _('Saudavel')

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
        resource_cost_status=resource_cost_status,
        evm_metrics=evm_metrics,
        risks=risks,
        compliance_status=compliance_status,
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
    resource_cost_status = calculate_resource_cost_status(project)
    evm_metrics = calculate_evm_metrics(project, schedule_status, cost_status)
    risks = identify_risks(project, schedule_status, cost_status)
    compliance_status = get_compliance_status(project)

    # Get additional data
    recent_activities = get_recent_activities(project)
    upcoming_milestones = get_upcoming_milestones(project)

    # Calculate overall health
    if any(r['severity'] == 'high' for r in risks) or compliance_status['status'] == 'red':
        overall_health = 'red'
        overall_label = _('Critico')
    elif any(r['severity'] == 'medium' for r in risks) or compliance_status['status'] == 'yellow':
        overall_health = 'yellow'
        overall_label = _('Atencao')
    else:
        overall_health = 'green'
        overall_label = _('Saudavel')

    team = Resource.query.filter_by(project_id=project_id, type='Pessoa', status='Ativo').all()
    total_hours = db.session.query(func.sum(Timesheet.hours))\
        .filter_by(project_id=project_id).scalar() or 0

    return render_template('status_report/print.html',
        project=project,
        tenant=tenant,
        report_date=datetime.now(),
        schedule_status=schedule_status,
        cost_status=cost_status,
        resource_cost_status=resource_cost_status,
        evm_metrics=evm_metrics,
        risks=risks,
        compliance_status=compliance_status,
        overall_health=overall_health,
        overall_label=overall_label,
        recent_activities=recent_activities,
        upcoming_milestones=upcoming_milestones,
        team=team,
        total_hours=total_hours
    )
