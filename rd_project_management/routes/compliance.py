"""
Compliance module routes - Central de Pendências e Conformidade de Projetos.
Supports global dashboard and lists with project filtering.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime, date
from sqlalchemy import or_

from models import (
    db, Project, User, Risk, PendingItem, NonConformity, Bug, CorrectiveAction
)
from services.tenant_utils import tenant_required, ensure_tenant_access, get_current_tenant_id

compliance_bp = Blueprint('compliance', __name__, url_prefix='/compliance')


def get_tenant_projects():
    """Get all projects for current tenant."""
    tenant_id = get_current_tenant_id()
    if tenant_id:
        return Project.query.filter_by(tenant_id=tenant_id).order_by(Project.title).all()
    return Project.query.order_by(Project.title).all()


def get_tenant_users():
    """Get all users for current tenant."""
    tenant_id = get_current_tenant_id()
    if tenant_id:
        return User.query.filter_by(tenant_id=tenant_id, active=True).order_by(User.full_name).all()
    return User.query.filter_by(active=True).order_by(User.full_name).all()


def generate_code(prefix, model, year=None):
    """Generate sequential code like NC-2024-001."""
    if year is None:
        year = date.today().year

    tenant_id = get_current_tenant_id()
    last_item = model.query.filter(
        model.code.like(f'{prefix}-{year}-%')
    )
    if hasattr(model, 'tenant_id') and tenant_id:
        last_item = last_item.filter_by(tenant_id=tenant_id)

    last_item = last_item.order_by(model.code.desc()).first()

    if last_item and last_item.code:
        try:
            last_num = int(last_item.code.split('-')[-1])
            next_num = last_num + 1
        except ValueError:
            next_num = 1
    else:
        next_num = 1

    return f"{prefix}-{year}-{next_num:03d}"


# ============================================================================
# DASHBOARD
# ============================================================================

@compliance_bp.route('/')
@login_required
@tenant_required
def dashboard():
    """Global compliance dashboard."""
    tenant_id = get_current_tenant_id()

    base_risk = Risk.query
    base_pending = PendingItem.query
    base_nc = NonConformity.query
    base_bug = Bug.query
    base_action = CorrectiveAction.query

    if tenant_id:
        base_risk = base_risk.filter_by(tenant_id=tenant_id)
        base_pending = base_pending.filter_by(tenant_id=tenant_id)
        base_nc = base_nc.filter_by(tenant_id=tenant_id)
        base_bug = base_bug.filter_by(tenant_id=tenant_id)
        base_action = base_action.filter_by(tenant_id=tenant_id)

    counts = {
        'risks': base_risk.filter(Risk.status.notin_(['Fechado', 'Mitigado'])).count(),
        'pending': base_pending.filter(PendingItem.status.notin_(['Resolvida', 'Cancelada'])).count(),
        'nc': base_nc.filter(NonConformity.status.notin_(['Fechada'])).count(),
        'bugs': base_bug.filter(Bug.status.notin_(['Resolvido', 'Fechado'])).count(),
        'actions': base_action.filter(CorrectiveAction.status.notin_(['Concluída', 'Verificada', 'Cancelada'])).count()
    }

    recent_items = []

    for risk in base_risk.order_by(Risk.created_at.desc()).limit(3).all():
        recent_items.append({'type': 'risk', 'title': risk.title, 'date': risk.created_at or date.today()})

    for item in base_pending.order_by(PendingItem.created_at.desc()).limit(3).all():
        recent_items.append({'type': 'pending', 'title': item.title, 'date': item.created_at or date.today()})

    for nc in base_nc.order_by(NonConformity.created_at.desc()).limit(3).all():
        recent_items.append({'type': 'nc', 'title': nc.title, 'date': nc.created_at or date.today()})

    for bug in base_bug.order_by(Bug.created_at.desc()).limit(3).all():
        recent_items.append({'type': 'bug', 'title': bug.title, 'date': bug.created_at or date.today()})

    for action in base_action.order_by(CorrectiveAction.created_at.desc()).limit(3).all():
        recent_items.append({'type': 'action', 'title': action.description[:50], 'date': action.created_at or date.today()})

    recent_items.sort(key=lambda x: x['date'], reverse=True)
    recent_items = recent_items[:10]

    return render_template('compliance/dashboard.html', counts=counts, recent_items=recent_items)


# ============================================================================
# RISCOS (RISKS)
# ============================================================================

@compliance_bp.route('/risks')
@login_required
@tenant_required
def risks_list():
    """List all risks."""
    tenant_id = get_current_tenant_id()
    status_filter = request.args.get('status', '')
    project_filter = request.args.get('project_id', '')

    risks = Risk.query
    if tenant_id:
        risks = risks.filter_by(tenant_id=tenant_id)

    if status_filter:
        risks = risks.filter_by(status=status_filter)
    if project_filter:
        risks = risks.filter_by(project_id=int(project_filter))

    risks = risks.order_by(Risk.created_at.desc()).all()
    projects = get_tenant_projects()

    return render_template('compliance/risks/list.html',
        risks=risks,
        projects=projects,
        status_filter=status_filter,
        project_filter=project_filter
    )


@compliance_bp.route('/risks/new', methods=['GET', 'POST'])
@login_required
@tenant_required
def risk_create():
    """Create a new risk."""
    tenant_id = get_current_tenant_id()

    if request.method == 'POST':
        project_id = request.form.get('project_id')
        owner_id = request.form.get('owner_id')
        identified_date = request.form.get('identified_date')
        probability = request.form.get('probability', 3)
        impact = request.form.get('impact', 3)

        # For superadmins, get tenant_id from the project
        effective_tenant_id = tenant_id
        if not effective_tenant_id and project_id:
            project = Project.query.get(int(project_id))
            if project:
                effective_tenant_id = project.tenant_id

        risk = Risk(
            tenant_id=effective_tenant_id,
            code=generate_code('RSK', Risk),
            project_id=int(project_id) if project_id else None,
            title=request.form.get('title', '').strip(),
            description=request.form.get('description', '').strip(),
            category=request.form.get('category', ''),
            probability=int(probability) if probability else 3,
            impact=int(impact) if impact else 3,
            status=request.form.get('status', 'Identificado'),
            response_strategy=request.form.get('response_strategy', ''),
            mitigation_plan=request.form.get('mitigation_plan', '').strip(),
            contingency_plan=request.form.get('contingency_plan', '').strip(),
            owner_id=int(owner_id) if owner_id else None,
            identified_date=datetime.strptime(identified_date, '%Y-%m-%d').date() if identified_date else date.today(),
            created_by_id=current_user.id
        )
        db.session.add(risk)
        db.session.commit()

        flash('Risco registrado com sucesso!', 'success')
        return redirect(url_for('compliance.risks_list'))

    projects = get_tenant_projects()
    users = get_tenant_users()
    return render_template('compliance/risks/form.html', risk=None, projects=projects, users=users)


@compliance_bp.route('/risks/<int:risk_id>/edit', methods=['GET', 'POST'])
@login_required
@tenant_required
def risk_edit(risk_id):
    """Edit a risk."""
    risk = Risk.query.get_or_404(risk_id)
    ensure_tenant_access(risk)

    if request.method == 'POST':
        project_id = request.form.get('project_id')
        owner_id = request.form.get('owner_id')
        identified_date = request.form.get('identified_date')
        probability = request.form.get('probability', 3)
        impact = request.form.get('impact', 3)

        risk.project_id = int(project_id) if project_id else None
        risk.title = request.form.get('title', '').strip()
        risk.description = request.form.get('description', '').strip()
        risk.category = request.form.get('category', '')
        risk.probability = int(probability) if probability else 3
        risk.impact = int(impact) if impact else 3
        risk.status = request.form.get('status', risk.status)
        risk.response_strategy = request.form.get('response_strategy', '')
        risk.mitigation_plan = request.form.get('mitigation_plan', '').strip()
        risk.contingency_plan = request.form.get('contingency_plan', '').strip()
        risk.owner_id = int(owner_id) if owner_id else None
        risk.identified_date = datetime.strptime(identified_date, '%Y-%m-%d').date() if identified_date else None

        db.session.commit()
        flash('Risco atualizado com sucesso!', 'success')
        return redirect(url_for('compliance.risks_list'))

    projects = get_tenant_projects()
    users = get_tenant_users()
    return render_template('compliance/risks/form.html', risk=risk, projects=projects, users=users)


@compliance_bp.route('/risks/<int:risk_id>/delete', methods=['POST'])
@login_required
@tenant_required
def risk_delete(risk_id):
    """Delete a risk."""
    risk = Risk.query.get_or_404(risk_id)
    ensure_tenant_access(risk)

    db.session.delete(risk)
    db.session.commit()
    flash('Risco excluído com sucesso!', 'success')
    return redirect(url_for('compliance.risks_list'))


# ============================================================================
# PENDÊNCIAS (PENDING ITEMS)
# ============================================================================

@compliance_bp.route('/pending')
@login_required
@tenant_required
def pending_list():
    """List all pending items."""
    tenant_id = get_current_tenant_id()
    status_filter = request.args.get('status', '')
    project_filter = request.args.get('project_id', '')

    items = PendingItem.query
    if tenant_id:
        items = items.filter_by(tenant_id=tenant_id)

    if status_filter:
        items = items.filter_by(status=status_filter)
    if project_filter:
        items = items.filter_by(project_id=int(project_filter))

    items = items.order_by(PendingItem.due_date.asc().nullslast()).all()
    projects = get_tenant_projects()

    return render_template('compliance/pending/list.html',
        items=items,
        projects=projects,
        status_filter=status_filter,
        project_filter=project_filter,
        now=date.today()
    )


@compliance_bp.route('/pending/new', methods=['GET', 'POST'])
@login_required
@tenant_required
def pending_create():
    """Create a new pending item."""
    tenant_id = get_current_tenant_id()

    if request.method == 'POST':
        project_id = request.form.get('project_id')
        responsible_id = request.form.get('responsible_id')
        due_date = request.form.get('due_date')
        resolution_date = request.form.get('resolution_date')

        # For superadmins, get tenant_id from the project
        effective_tenant_id = tenant_id
        if not effective_tenant_id and project_id:
            project = Project.query.get(int(project_id))
            if project:
                effective_tenant_id = project.tenant_id

        item = PendingItem(
            tenant_id=effective_tenant_id,
            code=generate_code('PND', PendingItem),
            project_id=int(project_id) if project_id else None,
            title=request.form.get('title', '').strip(),
            description=request.form.get('description', '').strip(),
            priority=request.form.get('priority', 'Média'),
            status=request.form.get('status', 'Aberta'),
            due_date=datetime.strptime(due_date, '%Y-%m-%d').date() if due_date else None,
            responsible_id=int(responsible_id) if responsible_id else None,
            resolution_date=datetime.strptime(resolution_date, '%Y-%m-%d').date() if resolution_date else None,
            resolution_notes=request.form.get('resolution_notes', '').strip(),
            created_by_id=current_user.id
        )
        db.session.add(item)
        db.session.commit()

        flash('Pendência registrada com sucesso!', 'success')
        return redirect(url_for('compliance.pending_list'))

    projects = get_tenant_projects()
    users = get_tenant_users()
    return render_template('compliance/pending/form.html', item=None, projects=projects, users=users)


@compliance_bp.route('/pending/<int:item_id>/edit', methods=['GET', 'POST'])
@login_required
@tenant_required
def pending_edit(item_id):
    """Edit a pending item."""
    item = PendingItem.query.get_or_404(item_id)
    ensure_tenant_access(item)

    if request.method == 'POST':
        project_id = request.form.get('project_id')
        responsible_id = request.form.get('responsible_id')
        due_date = request.form.get('due_date')
        resolution_date = request.form.get('resolution_date')

        item.project_id = int(project_id) if project_id else None
        item.title = request.form.get('title', '').strip()
        item.description = request.form.get('description', '').strip()
        item.priority = request.form.get('priority', 'Média')
        item.status = request.form.get('status', item.status)
        item.due_date = datetime.strptime(due_date, '%Y-%m-%d').date() if due_date else None
        item.responsible_id = int(responsible_id) if responsible_id else None
        item.resolution_date = datetime.strptime(resolution_date, '%Y-%m-%d').date() if resolution_date else None
        item.resolution_notes = request.form.get('resolution_notes', '').strip()

        db.session.commit()
        flash('Pendência atualizada com sucesso!', 'success')
        return redirect(url_for('compliance.pending_list'))

    projects = get_tenant_projects()
    users = get_tenant_users()
    return render_template('compliance/pending/form.html', item=item, projects=projects, users=users)


@compliance_bp.route('/pending/<int:item_id>/delete', methods=['POST'])
@login_required
@tenant_required
def pending_delete(item_id):
    """Delete a pending item."""
    item = PendingItem.query.get_or_404(item_id)
    ensure_tenant_access(item)

    db.session.delete(item)
    db.session.commit()
    flash('Pendência excluída com sucesso!', 'success')
    return redirect(url_for('compliance.pending_list'))


# ============================================================================
# NÃO CONFORMIDADES (NON-CONFORMITIES)
# ============================================================================

@compliance_bp.route('/nc')
@login_required
@tenant_required
def nc_list():
    """List all non-conformities."""
    tenant_id = get_current_tenant_id()
    status_filter = request.args.get('status', '')
    project_filter = request.args.get('project_id', '')

    items = NonConformity.query
    if tenant_id:
        items = items.filter_by(tenant_id=tenant_id)

    if status_filter:
        items = items.filter_by(status=status_filter)
    if project_filter:
        items = items.filter_by(project_id=int(project_filter))

    items = items.order_by(NonConformity.created_at.desc()).all()
    projects = get_tenant_projects()

    return render_template('compliance/nc/list.html',
        items=items,
        projects=projects,
        status_filter=status_filter,
        project_filter=project_filter
    )


@compliance_bp.route('/nc/new', methods=['GET', 'POST'])
@login_required
@tenant_required
def nc_create():
    """Create a new non-conformity."""
    tenant_id = get_current_tenant_id()

    if request.method == 'POST':
        project_id = request.form.get('project_id')
        responsible_id = request.form.get('responsible_id')
        identified_date = request.form.get('identified_date')
        closure_date = request.form.get('closure_date')

        # For superadmins, get tenant_id from the project
        effective_tenant_id = tenant_id
        if not effective_tenant_id and project_id:
            project = Project.query.get(int(project_id))
            if project:
                effective_tenant_id = project.tenant_id

        nc = NonConformity(
            tenant_id=effective_tenant_id,
            code=generate_code('NC', NonConformity),
            project_id=int(project_id) if project_id else None,
            title=request.form.get('title', '').strip(),
            description=request.form.get('description', '').strip(),
            nc_type=request.form.get('nc_type', ''),
            impact=request.form.get('impact', 'Médio'),
            status=request.form.get('status', 'Aberta'),
            root_cause=request.form.get('root_cause', '').strip(),
            corrective_plan=request.form.get('corrective_plan', '').strip(),
            evidence=request.form.get('evidence', '').strip(),
            responsible_id=int(responsible_id) if responsible_id else None,
            identified_date=datetime.strptime(identified_date, '%Y-%m-%d').date() if identified_date else date.today(),
            closure_date=datetime.strptime(closure_date, '%Y-%m-%d').date() if closure_date else None,
            created_by_id=current_user.id
        )
        db.session.add(nc)
        db.session.commit()

        flash('Não conformidade registrada com sucesso!', 'success')
        return redirect(url_for('compliance.nc_list'))

    projects = get_tenant_projects()
    users = get_tenant_users()
    return render_template('compliance/nc/form.html', item=None, projects=projects, users=users)


@compliance_bp.route('/nc/<int:nc_id>/edit', methods=['GET', 'POST'])
@login_required
@tenant_required
def nc_edit(nc_id):
    """Edit a non-conformity."""
    item = NonConformity.query.get_or_404(nc_id)
    ensure_tenant_access(item)

    if request.method == 'POST':
        project_id = request.form.get('project_id')
        responsible_id = request.form.get('responsible_id')
        identified_date = request.form.get('identified_date')
        closure_date = request.form.get('closure_date')

        item.project_id = int(project_id) if project_id else None
        item.title = request.form.get('title', '').strip()
        item.description = request.form.get('description', '').strip()
        item.nc_type = request.form.get('nc_type', '')
        item.impact = request.form.get('impact', 'Médio')
        item.status = request.form.get('status', item.status)
        item.root_cause = request.form.get('root_cause', '').strip()
        item.corrective_plan = request.form.get('corrective_plan', '').strip()
        item.evidence = request.form.get('evidence', '').strip()
        item.responsible_id = int(responsible_id) if responsible_id else None
        item.identified_date = datetime.strptime(identified_date, '%Y-%m-%d').date() if identified_date else None
        item.closure_date = datetime.strptime(closure_date, '%Y-%m-%d').date() if closure_date else None

        db.session.commit()
        flash('Não conformidade atualizada com sucesso!', 'success')
        return redirect(url_for('compliance.nc_list'))

    projects = get_tenant_projects()
    users = get_tenant_users()
    return render_template('compliance/nc/form.html', item=item, projects=projects, users=users)


@compliance_bp.route('/nc/<int:nc_id>/delete', methods=['POST'])
@login_required
@tenant_required
def nc_delete(nc_id):
    """Delete a non-conformity."""
    item = NonConformity.query.get_or_404(nc_id)
    ensure_tenant_access(item)

    db.session.delete(item)
    db.session.commit()
    flash('Não conformidade excluída com sucesso!', 'success')
    return redirect(url_for('compliance.nc_list'))


# ============================================================================
# BUGS
# ============================================================================

@compliance_bp.route('/bugs')
@login_required
@tenant_required
def bugs_list():
    """List all bugs."""
    tenant_id = get_current_tenant_id()
    status_filter = request.args.get('status', '')
    project_filter = request.args.get('project_id', '')

    bugs = Bug.query
    if tenant_id:
        bugs = bugs.filter_by(tenant_id=tenant_id)

    if status_filter:
        bugs = bugs.filter_by(status=status_filter)
    if project_filter:
        bugs = bugs.filter_by(project_id=int(project_filter))

    bugs = bugs.order_by(Bug.created_at.desc()).all()
    projects = get_tenant_projects()

    return render_template('compliance/bugs/list.html',
        bugs=bugs,
        projects=projects,
        status_filter=status_filter,
        project_filter=project_filter
    )


@compliance_bp.route('/bugs/new', methods=['GET', 'POST'])
@login_required
@tenant_required
def bug_create():
    """Create a new bug."""
    tenant_id = get_current_tenant_id()

    if request.method == 'POST':
        project_id = request.form.get('project_id')
        assigned_to_id = request.form.get('assigned_to_id')
        reported_date = request.form.get('reported_date')
        resolved_date = request.form.get('resolved_date')

        # For superadmins, get tenant_id from the project
        effective_tenant_id = tenant_id
        if not effective_tenant_id and project_id:
            project = Project.query.get(int(project_id))
            if project:
                effective_tenant_id = project.tenant_id

        bug = Bug(
            tenant_id=effective_tenant_id,
            code=generate_code('BUG', Bug),
            project_id=int(project_id) if project_id else None,
            title=request.form.get('title', '').strip(),
            description=request.form.get('description', '').strip(),
            severity=request.form.get('severity', 'Média'),
            environment=request.form.get('environment', 'Desenvolvimento'),
            status=request.form.get('status', 'Aberto'),
            steps_to_reproduce=request.form.get('steps_to_reproduce', '').strip(),
            expected_behavior=request.form.get('expected_behavior', '').strip(),
            actual_behavior=request.form.get('actual_behavior', '').strip(),
            evidence=request.form.get('evidence', '').strip(),
            assigned_to_id=int(assigned_to_id) if assigned_to_id else None,
            reported_date=datetime.strptime(reported_date, '%Y-%m-%d').date() if reported_date else date.today(),
            resolved_date=datetime.strptime(resolved_date, '%Y-%m-%d').date() if resolved_date else None,
            resolution_notes=request.form.get('resolution_notes', '').strip(),
            reported_by_id=current_user.id
        )
        db.session.add(bug)
        db.session.commit()

        flash('Bug registrado com sucesso!', 'success')
        return redirect(url_for('compliance.bugs_list'))

    projects = get_tenant_projects()
    users = get_tenant_users()
    return render_template('compliance/bugs/form.html', bug=None, projects=projects, users=users)


@compliance_bp.route('/bugs/<int:bug_id>/edit', methods=['GET', 'POST'])
@login_required
@tenant_required
def bug_edit(bug_id):
    """Edit a bug."""
    bug = Bug.query.get_or_404(bug_id)
    ensure_tenant_access(bug)

    if request.method == 'POST':
        project_id = request.form.get('project_id')
        assigned_to_id = request.form.get('assigned_to_id')
        reported_date = request.form.get('reported_date')
        resolved_date = request.form.get('resolved_date')

        bug.project_id = int(project_id) if project_id else None
        bug.title = request.form.get('title', '').strip()
        bug.description = request.form.get('description', '').strip()
        bug.severity = request.form.get('severity', 'Média')
        bug.environment = request.form.get('environment', 'Desenvolvimento')
        bug.status = request.form.get('status', bug.status)
        bug.steps_to_reproduce = request.form.get('steps_to_reproduce', '').strip()
        bug.expected_behavior = request.form.get('expected_behavior', '').strip()
        bug.actual_behavior = request.form.get('actual_behavior', '').strip()
        bug.evidence = request.form.get('evidence', '').strip()
        bug.assigned_to_id = int(assigned_to_id) if assigned_to_id else None
        bug.reported_date = datetime.strptime(reported_date, '%Y-%m-%d').date() if reported_date else None
        bug.resolved_date = datetime.strptime(resolved_date, '%Y-%m-%d').date() if resolved_date else None
        bug.resolution_notes = request.form.get('resolution_notes', '').strip()

        db.session.commit()
        flash('Bug atualizado com sucesso!', 'success')
        return redirect(url_for('compliance.bugs_list'))

    projects = get_tenant_projects()
    users = get_tenant_users()
    return render_template('compliance/bugs/form.html', bug=bug, projects=projects, users=users)


@compliance_bp.route('/bugs/<int:bug_id>/delete', methods=['POST'])
@login_required
@tenant_required
def bug_delete(bug_id):
    """Delete a bug."""
    bug = Bug.query.get_or_404(bug_id)
    ensure_tenant_access(bug)

    db.session.delete(bug)
    db.session.commit()
    flash('Bug excluído com sucesso!', 'success')
    return redirect(url_for('compliance.bugs_list'))


# ============================================================================
# AÇÕES CORRETIVAS (CORRECTIVE ACTIONS)
# ============================================================================

@compliance_bp.route('/actions')
@login_required
@tenant_required
def actions_list():
    """List all corrective actions."""
    tenant_id = get_current_tenant_id()
    status_filter = request.args.get('status', '')
    project_filter = request.args.get('project_id', '')

    actions = CorrectiveAction.query
    if tenant_id:
        actions = actions.filter_by(tenant_id=tenant_id)

    if status_filter:
        actions = actions.filter_by(status=status_filter)
    if project_filter:
        actions = actions.filter_by(project_id=int(project_filter))

    actions = actions.order_by(CorrectiveAction.due_date.asc().nullslast()).all()
    projects = get_tenant_projects()

    return render_template('compliance/actions/list.html',
        actions=actions,
        projects=projects,
        status_filter=status_filter,
        project_filter=project_filter,
        now=date.today()
    )


@compliance_bp.route('/actions/new', methods=['GET', 'POST'])
@login_required
@tenant_required
def action_create():
    """Create a new corrective action."""
    tenant_id = get_current_tenant_id()

    if request.method == 'POST':
        project_id = request.form.get('project_id')
        responsible_id = request.form.get('responsible_id')
        due_date = request.form.get('due_date')
        completion_date = request.form.get('completion_date')
        pending_item_id = request.form.get('pending_item_id')
        non_conformity_id = request.form.get('non_conformity_id')
        bug_id = request.form.get('bug_id')
        risk_id = request.form.get('risk_id')

        # For superadmins, get tenant_id from the project
        effective_tenant_id = tenant_id
        if not effective_tenant_id and project_id:
            project = Project.query.get(int(project_id))
            if project:
                effective_tenant_id = project.tenant_id

        action = CorrectiveAction(
            tenant_id=effective_tenant_id,
            code=generate_code('AC', CorrectiveAction),
            project_id=int(project_id) if project_id else None,
            description=request.form.get('description', '').strip(),
            action_type=request.form.get('action_type', 'Corretiva'),
            status=request.form.get('status', 'Planejada'),
            responsible_id=int(responsible_id) if responsible_id else None,
            due_date=datetime.strptime(due_date, '%Y-%m-%d').date() if due_date else None,
            completion_date=datetime.strptime(completion_date, '%Y-%m-%d').date() if completion_date else None,
            effectiveness=request.form.get('effectiveness', ''),
            verification_notes=request.form.get('verification_notes', '').strip(),
            pending_item_id=int(pending_item_id) if pending_item_id else None,
            non_conformity_id=int(non_conformity_id) if non_conformity_id else None,
            bug_id=int(bug_id) if bug_id else None,
            risk_id=int(risk_id) if risk_id else None,
            created_by_id=current_user.id
        )
        db.session.add(action)
        db.session.commit()

        flash('Ação corretiva registrada com sucesso!', 'success')
        return redirect(url_for('compliance.actions_list'))

    projects = get_tenant_projects()
    users = get_tenant_users()

    pending_items = PendingItem.query
    non_conformities = NonConformity.query
    bugs = Bug.query
    risks = Risk.query

    if tenant_id:
        pending_items = pending_items.filter_by(tenant_id=tenant_id)
        non_conformities = non_conformities.filter_by(tenant_id=tenant_id)
        bugs = bugs.filter_by(tenant_id=tenant_id)
        risks = risks.filter_by(tenant_id=tenant_id)

    return render_template('compliance/actions/form.html',
        action=None,
        projects=projects,
        users=users,
        pending_items=pending_items.all(),
        non_conformities=non_conformities.all(),
        bugs=bugs.all(),
        risks=risks.all()
    )


@compliance_bp.route('/actions/<int:action_id>/edit', methods=['GET', 'POST'])
@login_required
@tenant_required
def action_edit(action_id):
    """Edit a corrective action."""
    action = CorrectiveAction.query.get_or_404(action_id)
    ensure_tenant_access(action)
    tenant_id = get_current_tenant_id()

    if request.method == 'POST':
        project_id = request.form.get('project_id')
        responsible_id = request.form.get('responsible_id')
        due_date = request.form.get('due_date')
        completion_date = request.form.get('completion_date')
        pending_item_id = request.form.get('pending_item_id')
        non_conformity_id = request.form.get('non_conformity_id')
        bug_id = request.form.get('bug_id')
        risk_id = request.form.get('risk_id')

        action.project_id = int(project_id) if project_id else None
        action.description = request.form.get('description', '').strip()
        action.action_type = request.form.get('action_type', 'Corretiva')
        action.status = request.form.get('status', action.status)
        action.responsible_id = int(responsible_id) if responsible_id else None
        action.due_date = datetime.strptime(due_date, '%Y-%m-%d').date() if due_date else None
        action.completion_date = datetime.strptime(completion_date, '%Y-%m-%d').date() if completion_date else None
        action.effectiveness = request.form.get('effectiveness', '')
        action.verification_notes = request.form.get('verification_notes', '').strip()
        action.pending_item_id = int(pending_item_id) if pending_item_id else None
        action.non_conformity_id = int(non_conformity_id) if non_conformity_id else None
        action.bug_id = int(bug_id) if bug_id else None
        action.risk_id = int(risk_id) if risk_id else None

        db.session.commit()
        flash('Ação corretiva atualizada com sucesso!', 'success')
        return redirect(url_for('compliance.actions_list'))

    projects = get_tenant_projects()
    users = get_tenant_users()

    pending_items = PendingItem.query
    non_conformities = NonConformity.query
    bugs = Bug.query
    risks = Risk.query

    if tenant_id:
        pending_items = pending_items.filter_by(tenant_id=tenant_id)
        non_conformities = non_conformities.filter_by(tenant_id=tenant_id)
        bugs = bugs.filter_by(tenant_id=tenant_id)
        risks = risks.filter_by(tenant_id=tenant_id)

    return render_template('compliance/actions/form.html',
        action=action,
        projects=projects,
        users=users,
        pending_items=pending_items.all(),
        non_conformities=non_conformities.all(),
        bugs=bugs.all(),
        risks=risks.all()
    )


@compliance_bp.route('/actions/<int:action_id>/delete', methods=['POST'])
@login_required
@tenant_required
def action_delete(action_id):
    """Delete a corrective action."""
    action = CorrectiveAction.query.get_or_404(action_id)
    ensure_tenant_access(action)

    db.session.delete(action)
    db.session.commit()
    flash('Ação corretiva excluída com sucesso!', 'success')
    return redirect(url_for('compliance.actions_list'))
