from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file
from flask_login import login_required, current_user
from flask_babel import _
from models import db, Timesheet, Project, Milestone, Resource, AuditLog
from services.tenant_utils import tenant_required, ensure_tenant_access, get_current_tenant_id
from services.excel_timesheet import create_timesheet_template, parse_timesheet_excel
from datetime import datetime, date
from werkzeug.utils import secure_filename

timesheet_bp = Blueprint('timesheet', __name__)


@timesheet_bp.route('/projects/<int:project_id>/timesheet')
@login_required
@tenant_required
def list_timesheet(project_id):
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

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
@tenant_required
def create_entry(project_id):
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    tenant_id = get_current_tenant_id()

    if request.method == 'POST':
        entry = Timesheet(
            tenant_id=tenant_id,
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
        flash(_('Registro de horas adicionado com sucesso!'), 'success')
        return redirect(url_for('timesheet.list_timesheet', project_id=project_id))

    milestones = Milestone.query.filter_by(project_id=project_id).all()
    resources = Resource.query.filter_by(project_id=project_id, type='Pessoa', status='Ativo').all()
    return render_template('timesheet/form.html', project=project, entry=None, milestones=milestones, resources=resources)


@timesheet_bp.route('/projects/<int:project_id>/timesheet/<int:entry_id>/edit', methods=['GET', 'POST'])
@login_required
@tenant_required
def edit_entry(project_id, entry_id):
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    entry = Timesheet.query.get_or_404(entry_id)
    ensure_tenant_access(entry)

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
        flash(_('Registro atualizado com sucesso!'), 'success')
        return redirect(url_for('timesheet.list_timesheet', project_id=project_id))

    milestones = Milestone.query.filter_by(project_id=project_id).all()
    resources = Resource.query.filter_by(project_id=project_id, type='Pessoa', status='Ativo').all()
    return render_template('timesheet/form.html', project=project, entry=entry, milestones=milestones, resources=resources)


@timesheet_bp.route('/projects/<int:project_id>/timesheet/<int:entry_id>/delete', methods=['POST'])
@login_required
@tenant_required
def delete_entry(project_id, entry_id):
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    entry = Timesheet.query.get_or_404(entry_id)
    ensure_tenant_access(entry)

    db.session.delete(entry)
    db.session.commit()
    flash(_('Registro excluído com sucesso!'), 'success')
    return redirect(url_for('timesheet.list_timesheet', project_id=project_id))


@timesheet_bp.route('/projects/<int:project_id>/timesheet/template')
@login_required
@tenant_required
def download_template(project_id):
    """Download Excel template for timesheet import."""
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    milestones = Milestone.query.filter_by(project_id=project_id).all()
    resources = Resource.query.filter_by(project_id=project_id, type='Pessoa', status='Ativo').all()

    output = create_timesheet_template(project, milestones, resources)
    filename = f"timesheet_template_{project.id}.xlsx"

    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )


@timesheet_bp.route('/projects/<int:project_id>/timesheet/upload', methods=['GET', 'POST'])
@login_required
@tenant_required
def upload_excel(project_id):
    """Upload Excel file with timesheet entries."""
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    tenant_id = get_current_tenant_id()

    if request.method == 'POST':
        if 'file' not in request.files:
            flash(_('Nenhum arquivo selecionado.'), 'danger')
            return redirect(request.url)

        file = request.files['file']
        if file.filename == '':
            flash(_('Nenhum arquivo selecionado.'), 'danger')
            return redirect(request.url)

        if not file.filename.endswith(('.xlsx', '.xls')):
            flash(_('Formato inválido. Use arquivos Excel (.xlsx ou .xls).'), 'danger')
            return redirect(request.url)

        try:
            milestones = Milestone.query.filter_by(project_id=project_id).all()
            resources = Resource.query.filter_by(project_id=project_id, type='Pessoa', status='Ativo').all()

            entries, errors = parse_timesheet_excel(
                file,
                project_id=project_id,
                tenant_id=tenant_id,
                user_id=current_user.id,
                milestones=milestones,
                resources=resources
            )

            if errors and not entries:
                for error in errors[:5]:
                    flash(error, 'danger')
                if len(errors) > 5:
                    flash(_('... e mais %(count)s erros', count=len(errors) - 5), 'danger')
                return redirect(request.url)

            imported_count = 0
            for entry_data in entries:
                entry = Timesheet(**entry_data)
                db.session.add(entry)
                imported_count += 1

            db.session.commit()

            try:
                AuditLog.log(
                    action='import',
                    entity_type='timesheet',
                    entity_id=project_id,
                    entity_name=project.title,
                    details=f'Importados {imported_count} registros via Excel'
                )
                db.session.commit()
            except Exception:
                pass

            if errors:
                flash(_('%(count)s registros importados com sucesso! %(errors)s linhas com erro foram ignoradas.', count=imported_count, errors=len(errors)), 'warning')
            else:
                flash(_('%(count)s registros importados com sucesso!', count=imported_count), 'success')

            return redirect(url_for('timesheet.list_timesheet', project_id=project_id))

        except Exception as e:
            db.session.rollback()
            flash(_('Erro ao processar arquivo: %(error)s', error=str(e)), 'danger')
            return redirect(request.url)

    return render_template('timesheet/upload.html', project=project)
