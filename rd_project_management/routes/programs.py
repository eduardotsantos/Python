"""
Programs routes - manage groups of related projects.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date
from sqlalchemy import func

from models import db, Program, Project, Expense, Milestone, Resource, Timesheet, Risk, PendingItem, NonConformity, Bug, CorrectiveAction
from services.tenant_utils import tenant_required, ensure_tenant_access, get_current_tenant_id

programs_bp = Blueprint('programs', __name__)


@programs_bp.route('/programs')
@login_required
@tenant_required
def list_programs():
    """List all programs."""
    tenant_id = get_current_tenant_id()

    if tenant_id:
        programs = Program.query.filter_by(tenant_id=tenant_id).order_by(Program.name).all()
    else:
        # Superadmin sees all programs
        programs = Program.query.order_by(Program.name).all()

    programs_data = []
    for program in programs:
        projects = Project.query.filter_by(program_id=program.id).all()
        total_budget = sum(p.budget or 0 for p in projects)
        total_spent = db.session.query(func.sum(Expense.amount)).filter(
            Expense.project_id.in_([p.id for p in projects])
        ).scalar() or 0

        milestones = Milestone.query.filter(
            Milestone.project_id.in_([p.id for p in projects])
        ).all()
        total_progress = sum(m.progress or 0 for m in milestones) / len(milestones) if milestones else 0

        programs_data.append({
            'program': program,
            'project_count': len(projects),
            'total_budget': total_budget,
            'total_spent': total_spent,
            'progress': round(total_progress, 1)
        })

    return render_template('programs/list.html', programs_data=programs_data)


@programs_bp.route('/programs/create', methods=['GET', 'POST'])
@login_required
@tenant_required
def create_program():
    """Create a new program."""
    tenant_id = get_current_tenant_id()

    if not tenant_id:
        flash('Superadmins devem acessar via contexto de uma empresa para criar programas.', 'warning')
        return redirect(url_for('programs.list_programs'))

    if request.method == 'POST':
        program = Program(
            tenant_id=tenant_id,
            code=request.form['code'],
            name=request.form['name'],
            description=request.form.get('description'),
            objective=request.form.get('objective'),
            start_date=datetime.strptime(request.form['start_date'], '%Y-%m-%d').date() if request.form.get('start_date') else None,
            end_date=datetime.strptime(request.form['end_date'], '%Y-%m-%d').date() if request.form.get('end_date') else None,
            budget=float(request.form.get('budget') or 0),
            manager_id=int(request.form['manager_id']) if request.form.get('manager_id') else None,
            status=request.form.get('status', 'Ativo')
        )
        db.session.add(program)
        db.session.commit()
        flash('Programa criado com sucesso!', 'success')
        return redirect(url_for('programs.view_program', program_id=program.id))

    from models import User
    users = User.query.filter_by(tenant_id=tenant_id, active=True).all()
    return render_template('programs/form.html', program=None, users=users)


@programs_bp.route('/programs/<int:program_id>')
@login_required
@tenant_required
def view_program(program_id):
    """View program details."""
    program = Program.query.get_or_404(program_id)
    ensure_tenant_access(program)

    projects = Project.query.filter_by(program_id=program_id).all()

    # Calculate stats
    total_budget = sum(p.budget or 0 for p in projects)
    total_spent = db.session.query(func.sum(Expense.amount)).filter(
        Expense.project_id.in_([p.id for p in projects])
    ).scalar() or 0

    # Get all milestones
    milestones = Milestone.query.filter(
        Milestone.project_id.in_([p.id for p in projects])
    ).order_by(Milestone.end_date).all()

    total_progress = sum(m.progress or 0 for m in milestones) / len(milestones) if milestones else 0

    # Get unlinked projects for adding
    unlinked_projects = Project.query.filter_by(
        tenant_id=get_current_tenant_id(),
        program_id=None
    ).all()

    return render_template('programs/view.html',
        program=program,
        projects=projects,
        total_budget=total_budget,
        total_spent=total_spent,
        progress=round(total_progress, 1),
        milestones=milestones,
        unlinked_projects=unlinked_projects
    )


@programs_bp.route('/programs/<int:program_id>/edit', methods=['GET', 'POST'])
@login_required
@tenant_required
def edit_program(program_id):
    """Edit a program."""
    program = Program.query.get_or_404(program_id)
    ensure_tenant_access(program)

    if request.method == 'POST':
        program.code = request.form['code']
        program.name = request.form['name']
        program.description = request.form.get('description')
        program.objective = request.form.get('objective')
        program.start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date() if request.form.get('start_date') else None
        program.end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d').date() if request.form.get('end_date') else None
        program.budget = float(request.form.get('budget') or 0)
        program.manager_id = int(request.form['manager_id']) if request.form.get('manager_id') else None
        program.status = request.form.get('status', 'Ativo')

        db.session.commit()
        flash('Programa atualizado com sucesso!', 'success')
        return redirect(url_for('programs.view_program', program_id=program.id))

    from models import User
    users = User.query.filter_by(tenant_id=get_current_tenant_id(), active=True).all()
    return render_template('programs/form.html', program=program, users=users)


@programs_bp.route('/programs/<int:program_id>/delete', methods=['POST'])
@login_required
@tenant_required
def delete_program(program_id):
    """Delete a program."""
    program = Program.query.get_or_404(program_id)
    ensure_tenant_access(program)

    # Unlink projects
    Project.query.filter_by(program_id=program_id).update({'program_id': None})

    db.session.delete(program)
    db.session.commit()
    flash('Programa excluido com sucesso!', 'success')
    return redirect(url_for('programs.list_programs'))


@programs_bp.route('/programs/<int:program_id>/add-project', methods=['POST'])
@login_required
@tenant_required
def add_project_to_program(program_id):
    """Add a project to the program."""
    program = Program.query.get_or_404(program_id)
    ensure_tenant_access(program)

    project_id = request.form.get('project_id')
    if project_id:
        project = Project.query.get(project_id)
        if project and project.tenant_id == get_current_tenant_id():
            project.program_id = program_id
            db.session.commit()
            flash(f'Projeto {project.code} adicionado ao programa!', 'success')

    return redirect(url_for('programs.view_program', program_id=program_id))


@programs_bp.route('/programs/<int:program_id>/remove-project/<int:project_id>', methods=['POST'])
@login_required
@tenant_required
def remove_project_from_program(program_id, project_id):
    """Remove a project from the program."""
    program = Program.query.get_or_404(program_id)
    ensure_tenant_access(program)

    project = Project.query.get(project_id)
    if project and project.program_id == program_id:
        project.program_id = None
        db.session.commit()
        flash(f'Projeto {project.code} removido do programa!', 'success')

    return redirect(url_for('programs.view_program', program_id=program_id))


@programs_bp.route('/programs/<int:program_id>/status-report')
@login_required
@tenant_required
def program_status_report(program_id):
    """Consolidated status report for all projects in a program."""
    program = Program.query.get_or_404(program_id)
    ensure_tenant_access(program)

    tenant = current_user.tenant
    projects = Project.query.filter_by(program_id=program_id).all()

    # Consolidated calculations
    total_budget = sum(p.budget or 0 for p in projects)
    total_spent = db.session.query(func.sum(Expense.amount)).filter(
        Expense.project_id.in_([p.id for p in projects])
    ).scalar() or 0

    # Schedule status
    all_milestones = Milestone.query.filter(
        Milestone.project_id.in_([p.id for p in projects])
    ).all()

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

    # Cost status
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
            'title': f'{delayed} marco(s) atrasado(s)',
            'description': 'Existem marcos com data de entrega ultrapassada',
            'action': 'Revisar cronogramas dos projetos'
        })
    if percent_used > 100:
        risks.append({
            'type': 'cost',
            'severity': 'high',
            'title': 'Orcamento do programa estourado',
            'description': f'Gasto excede orcamento em R$ {total_spent - total_budget:,.2f}',
            'action': 'Revisar alocacao de recursos'
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

    # Total hours
    total_hours = db.session.query(func.sum(Timesheet.hours)).filter(
        Timesheet.project_id.in_([p.id for p in projects])
    ).scalar() or 0

    # Team
    team = Resource.query.filter(
        Resource.project_id.in_([p.id for p in projects]),
        Resource.type == 'Pessoa',
        Resource.status == 'Ativo'
    ).all()

    # Get unique team members
    unique_team = {r.name: r for r in team}.values()

    # Upcoming milestones
    upcoming_milestones = Milestone.query.filter(
        Milestone.project_id.in_([p.id for p in projects]),
        Milestone.status != 'Concluido',
        Milestone.end_date >= today
    ).order_by(Milestone.end_date).limit(10).all()

    # Compliance status for all projects in program
    project_ids = [p.id for p in projects]

    all_risks = Risk.query.filter(Risk.project_id.in_(project_ids)).all()
    open_risks = [r for r in all_risks if r.status not in ['Fechado', 'Mitigado', 'Encerrado']]
    critical_risks = [r for r in open_risks if r.probability >= 4 and r.impact >= 4]

    all_pending = PendingItem.query.filter(PendingItem.project_id.in_(project_ids)).all()
    open_pending = [p for p in all_pending if p.status not in ['Concluída', 'Fechada', 'Resolvida']]
    overdue_pending = [p for p in open_pending if p.due_date and p.due_date < today]

    all_bugs = Bug.query.filter(Bug.project_id.in_(project_ids)).all()
    open_bugs = [b for b in all_bugs if b.status not in ['Fechado', 'Resolvido', 'Encerrado']]
    critical_bugs = [b for b in open_bugs if b.severity in ['Crítico', 'Crítica', 'Critical']]

    all_ncs = NonConformity.query.filter(NonConformity.project_id.in_(project_ids)).all()
    open_ncs = [nc for nc in all_ncs if nc.status not in ['Fechada', 'Encerrada', 'Resolvida']]

    all_actions = CorrectiveAction.query.filter(CorrectiveAction.project_id.in_(project_ids)).all()
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

    return render_template('programs/status_report.html',
        program=program,
        tenant=tenant,
        projects=projects,
        report_date=datetime.now(),
        schedule_status=schedule_status,
        cost_status=cost_status,
        risks=risks,
        overall_health=overall_health,
        overall_label=overall_label,
        total_hours=total_hours,
        team=list(unique_team),
        upcoming_milestones=upcoming_milestones,
        compliance_status=compliance_status
    )


@programs_bp.route('/programs/<int:program_id>/export-project')
@login_required
@tenant_required
def export_program_to_project(program_id):
    """Export consolidated program schedule to MS Project XML."""
    program = Program.query.get_or_404(program_id)
    ensure_tenant_access(program)

    from services.msproject_service import export_program_to_xml
    xml_content = export_program_to_xml(program)

    from flask import Response
    response = Response(
        xml_content,
        mimetype='application/xml',
        headers={'Content-Disposition': f'attachment; filename=program_{program.code}.xml'}
    )
    return response
