from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required
from models import db, Milestone, Project
from services.tenant_utils import tenant_required, ensure_tenant_access, get_current_tenant_id
from datetime import datetime

schedule_bp = Blueprint('schedule', __name__)


@schedule_bp.route('/projects/<int:project_id>/schedule')
@login_required
@tenant_required
def view_schedule(project_id):
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    milestones = Milestone.query.filter_by(project_id=project_id).order_by(Milestone.order, Milestone.start_date).all()
    return render_template('schedule/view.html', project=project, milestones=milestones)


@schedule_bp.route('/projects/<int:project_id>/schedule/new', methods=['GET', 'POST'])
@login_required
@tenant_required
def create_milestone(project_id):
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    tenant_id = get_current_tenant_id()

    if request.method == 'POST':
        milestone = Milestone(
            tenant_id=tenant_id,
            project_id=project_id,
            title=request.form.get('title', '').strip(),
            description=request.form.get('description', '').strip(),
            start_date=datetime.strptime(request.form.get('start_date', ''), '%Y-%m-%d').date(),
            end_date=datetime.strptime(request.form.get('end_date', ''), '%Y-%m-%d').date(),
            progress=int(request.form.get('progress', 0)),
            status=request.form.get('status', 'Pendente'),
            order=int(request.form.get('order', 0) or 0)
        )
        db.session.add(milestone)
        db.session.commit()
        flash('Marco adicionado com sucesso!', 'success')
        return redirect(url_for('schedule.view_schedule', project_id=project_id))

    return render_template('schedule/form.html', project=project, milestone=None)


@schedule_bp.route('/projects/<int:project_id>/schedule/<int:milestone_id>/edit', methods=['GET', 'POST'])
@login_required
@tenant_required
def edit_milestone(project_id, milestone_id):
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    milestone = Milestone.query.get_or_404(milestone_id)
    ensure_tenant_access(milestone)

    if request.method == 'POST':
        milestone.title = request.form.get('title', '').strip()
        milestone.description = request.form.get('description', '').strip()
        milestone.start_date = datetime.strptime(request.form.get('start_date', ''), '%Y-%m-%d').date()
        milestone.end_date = datetime.strptime(request.form.get('end_date', ''), '%Y-%m-%d').date()
        milestone.progress = int(request.form.get('progress', 0))
        milestone.status = request.form.get('status', 'Pendente')
        milestone.order = int(request.form.get('order', 0) or 0)

        db.session.commit()
        flash('Marco atualizado com sucesso!', 'success')
        return redirect(url_for('schedule.view_schedule', project_id=project_id))

    return render_template('schedule/form.html', project=project, milestone=milestone)


@schedule_bp.route('/projects/<int:project_id>/schedule/<int:milestone_id>/delete', methods=['POST'])
@login_required
@tenant_required
def delete_milestone(project_id, milestone_id):
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    milestone = Milestone.query.get_or_404(milestone_id)
    ensure_tenant_access(milestone)

    db.session.delete(milestone)
    db.session.commit()
    flash('Marco excluído com sucesso!', 'success')
    return redirect(url_for('schedule.view_schedule', project_id=project_id))


@schedule_bp.route('/projects/<int:project_id>/schedule/<int:milestone_id>/progress', methods=['POST'])
@login_required
@tenant_required
def update_progress(project_id, milestone_id):
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    milestone = Milestone.query.get_or_404(milestone_id)
    ensure_tenant_access(milestone)

    progress = request.json.get('progress', 0)
    milestone.progress = max(0, min(100, int(progress)))
    if milestone.progress == 100:
        milestone.status = 'Concluído'
    elif milestone.progress > 0:
        milestone.status = 'Em Andamento'
    db.session.commit()
    return jsonify({'success': True, 'progress': milestone.progress, 'status': milestone.status})
