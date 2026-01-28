from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, Project, User, Expense, Resource, Milestone, Timesheet
from datetime import datetime

projects_bp = Blueprint('projects', __name__)


@projects_bp.route('/')
@login_required
def dashboard():
    return redirect(url_for('projects.list_projects'))


@projects_bp.route('/projects')
@login_required
def list_projects():
    status_filter = request.args.get('status', '')
    search = request.args.get('search', '')

    query = Project.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    if search:
        query = query.filter(
            db.or_(
                Project.title.ilike(f'%{search}%'),
                Project.code.ilike(f'%{search}%'),
                Project.description.ilike(f'%{search}%')
            )
        )

    projects = query.order_by(Project.created_at.desc()).all()

    # Stats
    total = Project.query.count()
    in_progress = Project.query.filter_by(status='Em Andamento').count()
    completed = Project.query.filter_by(status='Concluído').count()
    planning = Project.query.filter_by(status='Planejamento').count()

    total_budget = db.session.query(db.func.sum(Project.budget)).scalar() or 0
    total_expenses = db.session.query(db.func.sum(Expense.amount)).filter(Expense.status != 'Rejeitada').scalar() or 0

    return render_template('projects/list.html',
                           projects=projects,
                           total=total,
                           in_progress=in_progress,
                           completed=completed,
                           planning=planning,
                           total_budget=total_budget,
                           total_expenses=total_expenses,
                           status_filter=status_filter,
                           search=search)


@projects_bp.route('/projects/new', methods=['GET', 'POST'])
@login_required
def create_project():
    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        status = request.form.get('status', 'Planejamento')
        category = request.form.get('category', '')
        start_date_str = request.form.get('start_date', '')
        end_date_str = request.form.get('end_date', '')
        budget = request.form.get('budget', 0)
        funding_source = request.form.get('funding_source', '')

        if not all([code, title]):
            flash('Código e título são obrigatórios.', 'danger')
            return render_template('projects/form.html', project=None, users=User.query.all())

        if Project.query.filter_by(code=code).first():
            flash('Código do projeto já existe.', 'danger')
            return render_template('projects/form.html', project=None, users=User.query.all())

        project = Project(
            code=code,
            title=title,
            description=description,
            status=status,
            category=category,
            budget=float(budget) if budget else 0,
            funding_source=funding_source,
            responsible_id=current_user.id
        )

        if start_date_str:
            project.start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        if end_date_str:
            project.end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

        db.session.add(project)
        db.session.commit()
        flash('Projeto criado com sucesso!', 'success')
        return redirect(url_for('projects.view_project', project_id=project.id))

    return render_template('projects/form.html', project=None, users=User.query.all())


@projects_bp.route('/projects/<int:project_id>')
@login_required
def view_project(project_id):
    project = Project.query.get_or_404(project_id)
    total_expenses = sum(e.amount for e in project.expenses if e.status != 'Rejeitada')
    total_hours = sum(t.hours for t in project.timesheets)
    resource_count = len(project.resources)
    milestone_progress = 0
    if project.milestones:
        milestone_progress = sum(m.progress for m in project.milestones) // len(project.milestones)

    return render_template('projects/view.html',
                           project=project,
                           total_expenses=total_expenses,
                           total_hours=total_hours,
                           resource_count=resource_count,
                           milestone_progress=milestone_progress)


@projects_bp.route('/projects/<int:project_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_project(project_id):
    project = Project.query.get_or_404(project_id)

    if request.method == 'POST':
        project.code = request.form.get('code', '').strip()
        project.title = request.form.get('title', '').strip()
        project.description = request.form.get('description', '').strip()
        project.status = request.form.get('status', 'Planejamento')
        project.category = request.form.get('category', '')
        project.budget = float(request.form.get('budget', 0) or 0)
        project.funding_source = request.form.get('funding_source', '')
        project.responsible_id = request.form.get('responsible_id') or current_user.id

        start_date_str = request.form.get('start_date', '')
        end_date_str = request.form.get('end_date', '')
        if start_date_str:
            project.start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        if end_date_str:
            project.end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

        db.session.commit()
        flash('Projeto atualizado com sucesso!', 'success')
        return redirect(url_for('projects.view_project', project_id=project.id))

    return render_template('projects/form.html', project=project, users=User.query.all())


@projects_bp.route('/projects/<int:project_id>/delete', methods=['POST'])
@login_required
def delete_project(project_id):
    project = Project.query.get_or_404(project_id)
    db.session.delete(project)
    db.session.commit()
    flash('Projeto excluído com sucesso!', 'success')
    return redirect(url_for('projects.list_projects'))
