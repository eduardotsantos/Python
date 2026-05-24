"""
Agile module routes - Kanban board, sprints, and agile charts.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from sqlalchemy import func

from models import db, Project, Milestone, Sprint, User, Timesheet, Resource
from services.tenant_utils import tenant_required, ensure_tenant_access, get_current_tenant_id

agile_bp = Blueprint('agile', __name__)


@agile_bp.route('/projects/<int:project_id>/agile')
@login_required
@tenant_required
def kanban_board(project_id):
    """Kanban board view for project milestones."""
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    sprint_id = request.args.get('sprint_id', type=int)

    # Get milestones grouped by status
    query = Milestone.query.filter_by(project_id=project_id)
    if sprint_id:
        query = query.filter_by(sprint_id=sprint_id)

    milestones = query.order_by(Milestone.order, Milestone.priority.desc()).all()

    # Group by status
    backlog = [m for m in milestones if m.status == 'Pendente']
    in_progress = [m for m in milestones if m.status == 'Em Andamento']
    completed = [m for m in milestones if m.status in ['Concluído', 'Concluido']]

    # Get sprints
    sprints = Sprint.query.filter_by(project_id=project_id).order_by(Sprint.number.desc()).all()
    current_sprint = Sprint.query.filter_by(project_id=project_id, status='Ativo').first()

    # Get team members (resources) for assignment
    team = Resource.query.filter_by(project_id=project_id, type='Pessoa', status='Ativo').all()

    return render_template('agile/kanban.html',
        project=project,
        backlog=backlog,
        in_progress=in_progress,
        completed=completed,
        sprints=sprints,
        current_sprint=current_sprint,
        selected_sprint_id=sprint_id,
        team=team
    )


@agile_bp.route('/projects/<int:project_id>/agile/move', methods=['POST'])
@login_required
@tenant_required
def move_card(project_id):
    """Move a milestone card to a different status."""
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    data = request.json
    milestone_id = data.get('milestone_id')
    new_status = data.get('status')
    new_order = data.get('order', 0)

    milestone = Milestone.query.get_or_404(milestone_id)
    ensure_tenant_access(milestone)

    milestone.status = new_status
    milestone.order = new_order

    # Update progress based on status
    if new_status == 'Pendente':
        milestone.progress = 0
    elif new_status == 'Em Andamento' and milestone.progress == 0:
        milestone.progress = 10
    elif new_status in ['Concluído', 'Concluido']:
        milestone.progress = 100

    db.session.commit()

    return jsonify({'success': True, 'progress': milestone.progress})


@agile_bp.route('/projects/<int:project_id>/agile/sprints')
@login_required
@tenant_required
def list_sprints(project_id):
    """List all sprints for a project."""
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    sprints = Sprint.query.filter_by(project_id=project_id).order_by(Sprint.number.desc()).all()

    sprints_data = []
    for sprint in sprints:
        milestones = Milestone.query.filter_by(sprint_id=sprint.id).all()
        total_points = sum(m.story_points or 0 for m in milestones)
        completed_points = sum(m.story_points or 0 for m in milestones if m.status in ['Concluído', 'Concluido'])
        
        sprints_data.append({
            'sprint': sprint,
            'total_milestones': len(milestones),
            'completed_milestones': len([m for m in milestones if m.status in ['Concluído', 'Concluido']]),
            'total_points': total_points,
            'completed_points': completed_points,
            'progress': round((completed_points / total_points * 100) if total_points > 0 else 0, 1)
        })

    return render_template('agile/sprints.html',
        project=project,
        sprints_data=sprints_data
    )


@agile_bp.route('/projects/<int:project_id>/agile/sprints/new', methods=['GET', 'POST'])
@login_required
@tenant_required
def create_sprint(project_id):
    """Create a new sprint."""
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)
    tenant_id = get_current_tenant_id()

    if request.method == 'POST':
        # Get next sprint number
        last_sprint = Sprint.query.filter_by(project_id=project_id).order_by(Sprint.number.desc()).first()
        next_number = (last_sprint.number + 1) if last_sprint else 1

        sprint = Sprint(
            tenant_id=tenant_id,
            project_id=project_id,
            name=request.form.get('name', f'Sprint {next_number}'),
            number=next_number,
            goal=request.form.get('goal', ''),
            start_date=datetime.strptime(request.form['start_date'], '%Y-%m-%d').date(),
            end_date=datetime.strptime(request.form['end_date'], '%Y-%m-%d').date(),
            status=request.form.get('status', 'Planejado')
        )
        db.session.add(sprint)
        db.session.commit()

        flash(f'Sprint "{sprint.name}" criado com sucesso!', 'success')
        return redirect(url_for('agile.list_sprints', project_id=project_id))

    # Default dates: 2 weeks from today
    default_start = date.today()
    default_end = default_start + timedelta(days=14)

    return render_template('agile/sprint_form.html',
        project=project,
        sprint=None,
        default_start=default_start,
        default_end=default_end
    )


@agile_bp.route('/projects/<int:project_id>/agile/sprints/<int:sprint_id>/edit', methods=['GET', 'POST'])
@login_required
@tenant_required
def edit_sprint(project_id, sprint_id):
    """Edit a sprint."""
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    sprint = Sprint.query.get_or_404(sprint_id)
    ensure_tenant_access(sprint)

    if request.method == 'POST':
        sprint.name = request.form.get('name', sprint.name)
        sprint.goal = request.form.get('goal', '')
        sprint.start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
        sprint.end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d').date()
        sprint.status = request.form.get('status', sprint.status)

        # Calculate velocity if completed
        if sprint.status == 'Concluído':
            milestones = Milestone.query.filter_by(sprint_id=sprint.id).all()
            sprint.velocity = sum(m.story_points or 0 for m in milestones if m.status in ['Concluído', 'Concluido'])

        db.session.commit()
        flash('Sprint atualizado com sucesso!', 'success')
        return redirect(url_for('agile.list_sprints', project_id=project_id))

    return render_template('agile/sprint_form.html',
        project=project,
        sprint=sprint,
        default_start=sprint.start_date,
        default_end=sprint.end_date
    )


@agile_bp.route('/projects/<int:project_id>/agile/sprints/<int:sprint_id>/delete', methods=['POST'])
@login_required
@tenant_required
def delete_sprint(project_id, sprint_id):
    """Delete a sprint."""
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    sprint = Sprint.query.get_or_404(sprint_id)
    ensure_tenant_access(sprint)

    # Remove sprint_id from milestones
    Milestone.query.filter_by(sprint_id=sprint_id).update({'sprint_id': None})

    db.session.delete(sprint)
    db.session.commit()
    flash('Sprint excluído com sucesso!', 'success')
    return redirect(url_for('agile.list_sprints', project_id=project_id))


@agile_bp.route('/projects/<int:project_id>/agile/sprints/<int:sprint_id>/activate', methods=['POST'])
@login_required
@tenant_required
def activate_sprint(project_id, sprint_id):
    """Activate a sprint (only one active at a time)."""
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    # Deactivate all sprints for this project
    Sprint.query.filter_by(project_id=project_id, status='Ativo').update({'status': 'Planejado'})

    # Activate selected sprint
    sprint = Sprint.query.get_or_404(sprint_id)
    sprint.status = 'Ativo'
    db.session.commit()

    flash(f'Sprint "{sprint.name}" ativado!', 'success')
    return redirect(url_for('agile.list_sprints', project_id=project_id))


@agile_bp.route('/projects/<int:project_id>/agile/charts')
@login_required
@tenant_required
def agile_charts(project_id):
    """Agile charts and metrics."""
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    sprint_id = request.args.get('sprint_id', type=int)

    # Get sprints for selector
    sprints = Sprint.query.filter_by(project_id=project_id).order_by(Sprint.number.desc()).all()
    current_sprint = Sprint.query.filter_by(project_id=project_id, status='Ativo').first()

    if sprint_id:
        selected_sprint = Sprint.query.get(sprint_id)
    else:
        selected_sprint = current_sprint

    # Burndown data
    burndown_data = []
    if selected_sprint:
        milestones = Milestone.query.filter_by(sprint_id=selected_sprint.id).all()
        total_points = sum(m.story_points or 0 for m in milestones)

        # Generate daily burndown
        current = selected_sprint.start_date
        end = min(selected_sprint.end_date, date.today())
        ideal_remaining = total_points
        days_total = (selected_sprint.end_date - selected_sprint.start_date).days or 1
        daily_burn = total_points / days_total

        while current <= end:
            # Calculate actual remaining points for this day
            completed_by_date = sum(
                m.story_points or 0 for m in milestones
                if m.status in ['Concluído', 'Concluido'] and m.end_date and m.end_date <= current
            )
            actual_remaining = total_points - completed_by_date

            burndown_data.append({
                'date': current.isoformat(),
                'ideal': max(0, round(ideal_remaining, 1)),
                'actual': actual_remaining
            })

            ideal_remaining -= daily_burn
            current += timedelta(days=1)

    # Velocity chart (last 6 sprints)
    completed_sprints = Sprint.query.filter_by(
        project_id=project_id,
        status='Concluído'
    ).order_by(Sprint.number.desc()).limit(6).all()

    velocity_data = []
    for sprint in reversed(completed_sprints):
        velocity_data.append({
            'sprint': sprint.name,
            'velocity': sprint.velocity or 0
        })

    # Average velocity
    avg_velocity = sum(s.velocity or 0 for s in completed_sprints) / len(completed_sprints) if completed_sprints else 0

    # Status distribution
    milestones = Milestone.query.filter_by(project_id=project_id).all()
    status_distribution = {
        'Pendente': len([m for m in milestones if m.status == 'Pendente']),
        'Em Andamento': len([m for m in milestones if m.status == 'Em Andamento']),
        'Concluído': len([m for m in milestones if m.status in ['Concluído', 'Concluido']])
    }

    # Priority distribution
    priority_distribution = {
        'Crítica': len([m for m in milestones if m.priority == 'Crítica']),
        'Alta': len([m for m in milestones if m.priority == 'Alta']),
        'Média': len([m for m in milestones if m.priority == 'Média']),
        'Baixa': len([m for m in milestones if m.priority == 'Baixa'])
    }

    # Team workload
    workload = {}
    for m in milestones:
        if m.responsible:
            name = m.responsible.name
            if name not in workload:
                workload[name] = {'total': 0, 'completed': 0}
            workload[name]['total'] += 1
            if m.status in ['Concluído', 'Concluido']:
                workload[name]['completed'] += 1

    return render_template('agile/charts.html',
        project=project,
        sprints=sprints,
        selected_sprint=selected_sprint,
        burndown_data=burndown_data,
        velocity_data=velocity_data,
        avg_velocity=round(avg_velocity, 1),
        status_distribution=status_distribution,
        priority_distribution=priority_distribution,
        workload=workload
    )


@agile_bp.route('/projects/<int:project_id>/agile/milestone/<int:milestone_id>/assign', methods=['POST'])
@login_required
@tenant_required
def assign_milestone(project_id, milestone_id):
    """Assign a milestone to a user."""
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    milestone = Milestone.query.get_or_404(milestone_id)
    ensure_tenant_access(milestone)

    data = request.json
    user_id = data.get('user_id')
    sprint_id = data.get('sprint_id')

    if user_id:
        milestone.responsible_id = int(user_id) if user_id else None
    if sprint_id is not None:
        milestone.sprint_id = int(sprint_id) if sprint_id else None

    db.session.commit()
    return jsonify({'success': True})


@agile_bp.route('/projects/<int:project_id>/agile/milestone/<int:milestone_id>/points', methods=['POST'])
@login_required
@tenant_required
def update_points(project_id, milestone_id):
    """Update story points for a milestone."""
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    milestone = Milestone.query.get_or_404(milestone_id)
    ensure_tenant_access(milestone)

    data = request.json
    milestone.story_points = int(data.get('points', 0))
    milestone.priority = data.get('priority', milestone.priority)

    db.session.commit()
    return jsonify({'success': True})
