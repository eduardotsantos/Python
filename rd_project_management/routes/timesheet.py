from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, Timesheet, Project, Milestone, Resource
from datetime import datetime, date

timesheet_bp = Blueprint('timesheet', __name__)


@timesheet_bp.route('/projects/<int:project_id>/timesheet')
@login_required
def list_timesheet(project_id):
    project = Project.query.get_or_404(project_id)
    month_filter = request.args.get('month', '')
    user_filter = request.args.get('user_id', '')

    query = Timesheet.query.filter_by(project_id=project_id)
    if user_filter:
        query = query.filter_by(user_id=int(user_filter))
    if month_filter:
        year, month = month_filter.split('-')
        query = query.filter(
            db.extract('year', Timesheet.date) == int(year),
            db.extract('month', Timesheet.date) == int(month)
        )

    entries = query.order_by(Timesheet.date.desc()).all()
    total_hours = sum(e.hours for e in entries)

    # Group by user
    hours_by_user = {}
    for entry in entries:
        user_name = entry.user.full_name
        hours_by_user[user_name] = hours_by_user.get(user_name, 0) + entry.hours

    return render_template('timesheet/list.html',
                           project=project,
                           entries=entries,
                           total_hours=total_hours,
                           hours_by_user=hours_by_user,
                           month_filter=month_filter,
                           user_filter=user_filter)


@timesheet_bp.route('/projects/<int:project_id>/timesheet/new', methods=['GET', 'POST'])
@login_required
def create_entry(project_id):
    project = Project.query.get_or_404(project_id)

    if request.method == 'POST':
        entry = Timesheet(
            project_id=project_id,
            user_id=current_user.id,
            date=datetime.strptime(request.form.get('date', ''), '%Y-%m-%d').date() if request.form.get('date') else date.today(),
            hours=float(request.form.get('hours', 0)),
            activity=request.form.get('activity', '').strip(),
            notes=request.form.get('notes', '').strip()
        )
        milestone_id = request.form.get('milestone_id')
        if milestone_id:
            entry.milestone_id = int(milestone_id)

        resource_id = request.form.get('resource_id')
        if resource_id:
            entry.resource_id = int(resource_id)

        db.session.add(entry)
        db.session.commit()
        flash('Registro de horas adicionado com sucesso!', 'success')
        return redirect(url_for('timesheet.list_timesheet', project_id=project_id))

    milestones = Milestone.query.filter_by(project_id=project_id).all()
    resources = Resource.query.filter_by(project_id=project_id, type='Pessoa', status='Ativo').all()
    return render_template('timesheet/form.html', project=project, entry=None, milestones=milestones, resources=resources)


@timesheet_bp.route('/projects/<int:project_id>/timesheet/<int:entry_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_entry(project_id, entry_id):
    project = Project.query.get_or_404(project_id)
    entry = Timesheet.query.get_or_404(entry_id)

    if request.method == 'POST':
        entry.date = datetime.strptime(request.form.get('date', ''), '%Y-%m-%d').date() if request.form.get('date') else entry.date
        entry.hours = float(request.form.get('hours', 0))
        entry.activity = request.form.get('activity', '').strip()
        entry.notes = request.form.get('notes', '').strip()
        milestone_id = request.form.get('milestone_id')
        entry.milestone_id = int(milestone_id) if milestone_id else None
        resource_id = request.form.get('resource_id')
        entry.resource_id = int(resource_id) if resource_id else None

        db.session.commit()
        flash('Registro atualizado com sucesso!', 'success')
        return redirect(url_for('timesheet.list_timesheet', project_id=project_id))

    milestones = Milestone.query.filter_by(project_id=project_id).all()
    resources = Resource.query.filter_by(project_id=project_id, type='Pessoa', status='Ativo').all()
    return render_template('timesheet/form.html', project=project, entry=entry, milestones=milestones, resources=resources)


@timesheet_bp.route('/projects/<int:project_id>/timesheet/<int:entry_id>/delete', methods=['POST'])
@login_required
def delete_entry(project_id, entry_id):
    entry = Timesheet.query.get_or_404(entry_id)
    db.session.delete(entry)
    db.session.commit()
    flash('Registro excluído com sucesso!', 'success')
    return redirect(url_for('timesheet.list_timesheet', project_id=project_id))
