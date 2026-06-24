from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file, current_app
from flask_login import login_required, current_user
from flask_babel import _
from models import db, Project, User, Expense, Resource, Milestone, Timesheet, ProjectCall, ProjectDocument, Tenant, ProjectStakeholder, ProjectTRLHistory
from services.tenant_utils import tenant_required, ensure_tenant_access, get_current_tenant_id
from datetime import datetime
from io import BytesIO
from werkzeug.utils import secure_filename
import uuid
import os
try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False

projects_bp = Blueprint('projects', __name__)

MAX_DOCUMENTS_PER_PROJECT = 3


def allowed_file(filename):
    """Check if file extension is allowed."""
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in current_app.config.get('ALLOWED_EXTENSIONS', {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'})


def get_file_extension(filename):
    """Get file extension."""
    if '.' in filename:
        return filename.rsplit('.', 1)[1].lower()
    return ''


def get_tenant_filter():
    """Get tenant filter for queries."""
    tenant_id = get_current_tenant_id()
    if tenant_id:
        return {'tenant_id': tenant_id}
    return {}


@projects_bp.route('/')
@login_required
@tenant_required
def dashboard():
    return redirect(url_for('projects.list_projects'))


@projects_bp.route('/projects')
@login_required
@tenant_required
def list_projects():
    status_filter = request.args.get('status', '')
    search = request.args.get('search', '')

    tenant_id = get_current_tenant_id()
    query = Project.query
    if tenant_id:
        query = query.filter_by(tenant_id=tenant_id)

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

    # Stats for current tenant
    base_query = Project.query
    if tenant_id:
        base_query = base_query.filter_by(tenant_id=tenant_id)

    total = base_query.count()
    in_progress = base_query.filter_by(status='Em Andamento').count()
    completed = base_query.filter_by(status='Concluído').count()
    planning = base_query.filter_by(status='Planejamento').count()

    # Budget stats for tenant
    if tenant_id:
        total_budget = db.session.query(db.func.sum(Project.budget)).filter(Project.tenant_id == tenant_id).scalar() or 0
        total_expenses = db.session.query(db.func.sum(Expense.amount)).filter(
            Expense.tenant_id == tenant_id,
            Expense.status != 'Rejeitada'
        ).scalar() or 0
    else:
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
@tenant_required
def create_project():
    tenant_id = get_current_tenant_id()
    is_superadmin = current_user.tenant_id is None

    # Get tenants for superadmin selection
    tenants = Tenant.query.filter_by(is_active=True).order_by(Tenant.name).all() if is_superadmin else []

    # Check tenant project limit
    if tenant_id and current_user.tenant and not current_user.tenant.can_add_project():
        flash(_('Limite de projetos atingido (%(max)s). Entre em contato com o suporte.', max=current_user.tenant.max_projects), 'warning')
        return redirect(url_for('projects.list_projects'))

    if request.method == 'POST':
        # For superadmin, get tenant from form
        if is_superadmin:
            selected_tenant_id = request.form.get('tenant_id')
            if not selected_tenant_id:
                flash(_('Selecione uma empresa para criar o projeto.'), 'danger')
                users = User.query.all()
                return render_template('projects/form.html', project=None, users=users, tenants=tenants, is_superadmin=is_superadmin)
            tenant_id = int(selected_tenant_id)

        code = request.form.get('code', '').strip()
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        status = request.form.get('status', 'Planejamento')
        category = request.form.get('category', '')
        start_date_str = request.form.get('start_date', '')
        end_date_str = request.form.get('end_date', '')
        budget = request.form.get('budget', 0)
        funding_source = request.form.get('funding_source', '')

        users = User.query.filter_by(tenant_id=tenant_id).all() if tenant_id else User.query.all()

        if not all([code, title]):
            flash(_('Código e título são obrigatórios.'), 'danger')
            return render_template('projects/form.html', project=None, users=users, tenants=tenants, is_superadmin=is_superadmin)

        # Check code uniqueness within tenant
        existing = Project.query.filter_by(tenant_id=tenant_id, code=code).first()
        if existing:
            flash(_('Código do projeto já existe nesta empresa.'), 'danger')
            return render_template('projects/form.html', project=None, users=users, tenants=tenants, is_superadmin=is_superadmin)

        # PMBOK 8 - Value fields
        value_type = request.form.get('value_type', '')
        expected_value = request.form.get('expected_value', 0)
        realized_value = request.form.get('realized_value', 0)
        value_status = request.form.get('value_status', 'Não iniciado')

        project = Project(
            tenant_id=tenant_id,
            code=code,
            title=title,
            description=description,
            status=status,
            category=category,
            budget=float(budget) if budget else 0,
            funding_source=funding_source,
            responsible_id=current_user.id,
            value_type=value_type,
            expected_value=float(expected_value) if expected_value else 0,
            realized_value=float(realized_value) if realized_value else 0,
            value_status=value_status
        )

        if start_date_str:
            project.start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        if end_date_str:
            project.end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

        db.session.add(project)
        db.session.commit()
        flash(_('Projeto criado com sucesso!'), 'success')
        return redirect(url_for('projects.view_project', project_id=project.id))

    users = User.query.filter_by(tenant_id=tenant_id).all() if tenant_id else User.query.all()
    return render_template('projects/form.html', project=None, users=users, tenants=tenants, is_superadmin=is_superadmin)


@projects_bp.route('/projects/<int:project_id>')
@login_required
@tenant_required
def view_project(project_id):
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

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
@tenant_required
def edit_project(project_id):
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    tenant_id = get_current_tenant_id() or project.tenant_id
    is_superadmin = current_user.tenant_id is None

    if request.method == 'POST':
        new_code = request.form.get('code', '').strip()

        # Check code uniqueness if changed
        if new_code != project.code:
            existing = Project.query.filter_by(tenant_id=project.tenant_id, code=new_code).first()
            if existing:
                flash(_('Código do projeto já existe.'), 'danger')
                users = User.query.filter_by(tenant_id=tenant_id).all() if tenant_id else User.query.all()
                return render_template('projects/form.html', project=project, users=users, tenants=[], is_superadmin=is_superadmin)

        project.code = new_code
        project.title = request.form.get('title', '').strip()
        project.description = request.form.get('description', '').strip()
        project.status = request.form.get('status', 'Planejamento')
        project.category = request.form.get('category', '')
        project.budget = float(request.form.get('budget', 0) or 0)
        project.funding_source = request.form.get('funding_source', '')
        project.responsible_id = request.form.get('responsible_id') or current_user.id

        # PMBOK 8 - Value fields
        project.value_type = request.form.get('value_type', '')
        project.expected_value = float(request.form.get('expected_value', 0) or 0)
        project.realized_value = float(request.form.get('realized_value', 0) or 0)
        project.value_status = request.form.get('value_status', 'Não iniciado')

        # TRL - Track history if changed
        new_trl = int(request.form.get('trl', 1) or 1)
        if new_trl != project.trl:
            trl_history = ProjectTRLHistory(
                tenant_id=project.tenant_id,
                project_id=project.id,
                trl_from=project.trl,
                trl_to=new_trl,
                change_date=datetime.now().date(),
                justification=request.form.get('trl_justification', ''),
                changed_by_id=current_user.id
            )
            db.session.add(trl_history)
            project.trl = new_trl

        # Innovation KPIs
        project.innovation_type = request.form.get('innovation_type', '')
        project.innovation_scope = request.form.get('innovation_scope', '')
        project.target_market = request.form.get('target_market', '')
        project.competitive_advantage = request.form.get('competitive_advantage', '')
        project.ip_strategy = request.form.get('ip_strategy', '')
        project.time_to_market = int(request.form.get('time_to_market', 0) or 0) or None
        project.expected_roi_percent = float(request.form.get('expected_roi_percent', 0) or 0) or None
        project.innovation_risk_level = request.form.get('innovation_risk_level', '')

        start_date_str = request.form.get('start_date', '')
        end_date_str = request.form.get('end_date', '')
        if start_date_str:
            project.start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        if end_date_str:
            project.end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

        db.session.commit()
        flash(_('Projeto atualizado com sucesso!'), 'success')
        return redirect(url_for('projects.view_project', project_id=project.id))

    users = User.query.filter_by(tenant_id=tenant_id).all() if tenant_id else User.query.all()
    return render_template('projects/form.html', project=project, users=users, tenants=[], is_superadmin=is_superadmin)


@projects_bp.route('/projects/<int:project_id>/delete', methods=['POST'])
@login_required
@tenant_required
def delete_project(project_id):
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    db.session.delete(project)
    db.session.commit()
    flash(_('Projeto excluído com sucesso!'), 'success')
    return redirect(url_for('projects.list_projects'))


@projects_bp.route('/projects/<int:project_id>/export-msproject')
@login_required
@tenant_required
def export_to_msproject(project_id):
    """Export project schedule to MS Project XML format."""
    from flask import Response
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    from services.msproject_service import export_project_to_xml
    xml_content = export_project_to_xml(project)

    response = Response(
        xml_content,
        mimetype='application/xml',
        headers={'Content-Disposition': f'attachment; filename=project_{project.code}.xml'}
    )
    return response


@projects_bp.route('/projects/<int:project_id>/import-msproject', methods=['POST'])
@login_required
@tenant_required
def import_from_msproject(project_id):
    """Import milestones from MS Project XML file."""
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    if 'file' not in request.files:
        flash(_('Nenhum arquivo selecionado.'), 'danger')
        return redirect(url_for('schedule.schedule_view', project_id=project_id))

    file = request.files['file']
    if file.filename == '':
        flash(_('Nenhum arquivo selecionado.'), 'danger')
        return redirect(url_for('schedule.schedule_view', project_id=project_id))

    if not file.filename.lower().endswith('.xml'):
        flash(_('Arquivo deve ser XML do MS Project.'), 'danger')
        return redirect(url_for('schedule.schedule_view', project_id=project_id))

    try:
        xml_content = file.read().decode('utf-8')
        from services.msproject_service import import_project_from_xml
        count, message = import_project_from_xml(xml_content, project)
        flash(message, 'success' if count > 0 else 'warning')
    except Exception as e:
        flash(_('Erro ao importar arquivo: %(err)s', err=str(e)), 'danger')

    return redirect(url_for('schedule.schedule_view', project_id=project_id))


@projects_bp.route('/projects/export-excel')
@login_required
@tenant_required
def export_excel():
    """Export all projects to Excel with multiple sheets."""
    if not EXCEL_AVAILABLE:
        flash(_('Funcionalidade de exportação Excel não disponível. Instale openpyxl.'), 'danger')
        return redirect(url_for('projects.list_projects'))

    tenant_id = get_current_tenant_id()

    # Filter all queries by tenant
    if tenant_id:
        projects = Project.query.filter_by(tenant_id=tenant_id).order_by(Project.created_at.desc()).all()
    else:
        projects = Project.query.order_by(Project.created_at.desc()).all()

    wb = Workbook()

    # Style definitions
    header_font = Font(bold=True, color='FFFFFF')
    header_fill = PatternFill(start_color='0066CC', end_color='0066CC', fill_type='solid')
    header_alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )

    # Sheet 1: Projects (Dados Gerais)
    ws_projects = wb.active
    ws_projects.title = 'Projetos'
    project_headers = ['ID', 'Código', 'Título', 'Descrição', 'Status', 'Categoria',
                       'Data Início', 'Data Fim', 'Orçamento (R$)', 'Fonte de Recursos',
                       'Responsável', 'Criado em', 'Atualizado em']
    _write_headers(ws_projects, project_headers, header_font, header_fill, header_alignment, thin_border)

    for row_idx, project in enumerate(projects, start=2):
        ws_projects.cell(row=row_idx, column=1, value=project.id)
        ws_projects.cell(row=row_idx, column=2, value=project.code)
        ws_projects.cell(row=row_idx, column=3, value=project.title)
        ws_projects.cell(row=row_idx, column=4, value=project.description or '')
        ws_projects.cell(row=row_idx, column=5, value=project.status)
        ws_projects.cell(row=row_idx, column=6, value=project.category or '')
        ws_projects.cell(row=row_idx, column=7, value=project.start_date.strftime('%d/%m/%Y') if project.start_date else '')
        ws_projects.cell(row=row_idx, column=8, value=project.end_date.strftime('%d/%m/%Y') if project.end_date else '')
        ws_projects.cell(row=row_idx, column=9, value=project.budget)
        ws_projects.cell(row=row_idx, column=10, value=project.funding_source or '')
        ws_projects.cell(row=row_idx, column=11, value=project.responsible.full_name if project.responsible else '')
        ws_projects.cell(row=row_idx, column=12, value=project.created_at.strftime('%d/%m/%Y %H:%M') if project.created_at else '')
        ws_projects.cell(row=row_idx, column=13, value=project.updated_at.strftime('%d/%m/%Y %H:%M') if project.updated_at else '')

    _auto_adjust_columns(ws_projects)

    # Sheet 2: Expenses (Despesas)
    ws_expenses = wb.create_sheet('Despesas')
    expense_headers = ['Projeto', 'Código Projeto', 'Descrição', 'Categoria', 'Valor (R$)',
                       'Data', 'Nº Recibo', 'Fornecedor', 'Status', 'Notas', 'Criado por', 'Criado em']
    _write_headers(ws_expenses, expense_headers, header_font, header_fill, header_alignment, thin_border)

    if tenant_id:
        expenses = Expense.query.filter_by(tenant_id=tenant_id).join(Project).order_by(Project.code, Expense.date.desc()).all()
    else:
        expenses = Expense.query.join(Project).order_by(Project.code, Expense.date.desc()).all()

    for row_idx, expense in enumerate(expenses, start=2):
        ws_expenses.cell(row=row_idx, column=1, value=expense.project.title)
        ws_expenses.cell(row=row_idx, column=2, value=expense.project.code)
        ws_expenses.cell(row=row_idx, column=3, value=expense.description)
        ws_expenses.cell(row=row_idx, column=4, value=expense.category)
        ws_expenses.cell(row=row_idx, column=5, value=expense.amount)
        ws_expenses.cell(row=row_idx, column=6, value=expense.date.strftime('%d/%m/%Y') if expense.date else '')
        ws_expenses.cell(row=row_idx, column=7, value=expense.receipt_number or '')
        ws_expenses.cell(row=row_idx, column=8, value=expense.supplier or '')
        ws_expenses.cell(row=row_idx, column=9, value=expense.status)
        ws_expenses.cell(row=row_idx, column=10, value=expense.notes or '')
        ws_expenses.cell(row=row_idx, column=11, value=expense.created_by.full_name if expense.created_by else '')
        ws_expenses.cell(row=row_idx, column=12, value=expense.created_at.strftime('%d/%m/%Y %H:%M') if expense.created_at else '')

    _auto_adjust_columns(ws_expenses)

    # Sheet 3: Resources (Recursos)
    ws_resources = wb.create_sheet('Recursos')
    resource_headers = ['Projeto', 'Código Projeto', 'Tipo', 'Nome', 'Função',
                        'Horas Alocadas', 'Custo/Hora (R$)', 'Data Início', 'Data Fim', 'Status', 'Notas']
    _write_headers(ws_resources, resource_headers, header_font, header_fill, header_alignment, thin_border)

    if tenant_id:
        resources = Resource.query.filter_by(tenant_id=tenant_id).join(Project).order_by(Project.code).all()
    else:
        resources = Resource.query.join(Project).order_by(Project.code).all()

    for row_idx, resource in enumerate(resources, start=2):
        ws_resources.cell(row=row_idx, column=1, value=resource.project.title)
        ws_resources.cell(row=row_idx, column=2, value=resource.project.code)
        ws_resources.cell(row=row_idx, column=3, value=resource.type)
        ws_resources.cell(row=row_idx, column=4, value=resource.name)
        ws_resources.cell(row=row_idx, column=5, value=resource.role or '')
        ws_resources.cell(row=row_idx, column=6, value=resource.hours_allocated)
        ws_resources.cell(row=row_idx, column=7, value=resource.hourly_cost)
        ws_resources.cell(row=row_idx, column=8, value=resource.start_date.strftime('%d/%m/%Y') if resource.start_date else '')
        ws_resources.cell(row=row_idx, column=9, value=resource.end_date.strftime('%d/%m/%Y') if resource.end_date else '')
        ws_resources.cell(row=row_idx, column=10, value=resource.status)
        ws_resources.cell(row=row_idx, column=11, value=resource.notes or '')

    _auto_adjust_columns(ws_resources)

    # Sheet 4: Milestones (Cronograma)
    ws_milestones = wb.create_sheet('Cronograma')
    milestone_headers = ['Projeto', 'Código Projeto', 'Marco', 'Descrição',
                         'Data Início', 'Data Fim', 'Progresso (%)', 'Status', 'Ordem']
    _write_headers(ws_milestones, milestone_headers, header_font, header_fill, header_alignment, thin_border)

    if tenant_id:
        milestones = Milestone.query.filter_by(tenant_id=tenant_id).join(Project).order_by(Project.code, Milestone.order).all()
    else:
        milestones = Milestone.query.join(Project).order_by(Project.code, Milestone.order).all()

    for row_idx, milestone in enumerate(milestones, start=2):
        ws_milestones.cell(row=row_idx, column=1, value=milestone.project.title)
        ws_milestones.cell(row=row_idx, column=2, value=milestone.project.code)
        ws_milestones.cell(row=row_idx, column=3, value=milestone.title)
        ws_milestones.cell(row=row_idx, column=4, value=milestone.description or '')
        ws_milestones.cell(row=row_idx, column=5, value=milestone.start_date.strftime('%d/%m/%Y') if milestone.start_date else '')
        ws_milestones.cell(row=row_idx, column=6, value=milestone.end_date.strftime('%d/%m/%Y') if milestone.end_date else '')
        ws_milestones.cell(row=row_idx, column=7, value=milestone.progress)
        ws_milestones.cell(row=row_idx, column=8, value=milestone.status)
        ws_milestones.cell(row=row_idx, column=9, value=milestone.order)

    _auto_adjust_columns(ws_milestones)

    # Sheet 5: Timesheets (Apontamento de Horas)
    ws_timesheets = wb.create_sheet('Apontamento de Horas')
    timesheet_headers = ['Projeto', 'Código Projeto', 'Usuário', 'Data', 'Horas',
                         'Atividade', 'Marco', 'Recurso', 'Notas']
    _write_headers(ws_timesheets, timesheet_headers, header_font, header_fill, header_alignment, thin_border)

    if tenant_id:
        timesheets = Timesheet.query.filter_by(tenant_id=tenant_id).join(Project).order_by(Project.code, Timesheet.date.desc()).all()
    else:
        timesheets = Timesheet.query.join(Project).order_by(Project.code, Timesheet.date.desc()).all()

    for row_idx, ts in enumerate(timesheets, start=2):
        ws_timesheets.cell(row=row_idx, column=1, value=ts.project.title)
        ws_timesheets.cell(row=row_idx, column=2, value=ts.project.code)
        ws_timesheets.cell(row=row_idx, column=3, value=ts.user.full_name if ts.user else '')
        ws_timesheets.cell(row=row_idx, column=4, value=ts.date.strftime('%d/%m/%Y') if ts.date else '')
        ws_timesheets.cell(row=row_idx, column=5, value=ts.hours)
        ws_timesheets.cell(row=row_idx, column=6, value=ts.activity)
        ws_timesheets.cell(row=row_idx, column=7, value=ts.milestone.title if ts.milestone else '')
        ws_timesheets.cell(row=row_idx, column=8, value=ts.resource.name if ts.resource else '')
        ws_timesheets.cell(row=row_idx, column=9, value=ts.notes or '')

    _auto_adjust_columns(ws_timesheets)

    # Sheet 6: Project-Call Links (Chamadas Públicas Vinculadas)
    ws_calls = wb.create_sheet('Chamadas Vinculadas')
    call_headers = ['Projeto', 'Código Projeto', 'Chamada', 'Fonte', 'Tema',
                    'Data Vinculação', 'Status Vínculo', 'Notas']
    _write_headers(ws_calls, call_headers, header_font, header_fill, header_alignment, thin_border)

    if tenant_id:
        project_calls = ProjectCall.query.filter_by(tenant_id=tenant_id).join(Project).order_by(Project.code).all()
    else:
        project_calls = ProjectCall.query.join(Project).order_by(Project.code).all()

    for row_idx, pc in enumerate(project_calls, start=2):
        ws_calls.cell(row=row_idx, column=1, value=pc.project.title)
        ws_calls.cell(row=row_idx, column=2, value=pc.project.code)
        ws_calls.cell(row=row_idx, column=3, value=pc.public_call.title if pc.public_call else '')
        ws_calls.cell(row=row_idx, column=4, value=pc.public_call.source if pc.public_call else '')
        ws_calls.cell(row=row_idx, column=5, value=pc.public_call.theme if pc.public_call else '')
        ws_calls.cell(row=row_idx, column=6, value=pc.linked_at.strftime('%d/%m/%Y') if pc.linked_at else '')
        ws_calls.cell(row=row_idx, column=7, value=pc.status)
        ws_calls.cell(row=row_idx, column=8, value=pc.notes or '')

    _auto_adjust_columns(ws_calls)

    # Save to BytesIO
    output = BytesIO()
    wb.save(output)
    output.seek(0)

    tenant_name = current_user.tenant.slug if current_user.tenant else 'all'
    filename = f'projetos_pd_{tenant_name}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'

    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )


def _write_headers(ws, headers, font, fill, alignment, border):
    """Write headers to a worksheet with styling."""
    for col_idx, header in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = font
        cell.fill = fill
        cell.alignment = alignment
        cell.border = border


def _auto_adjust_columns(ws):
    """Auto-adjust column widths based on content."""
    for column in ws.columns:
        max_length = 0
        column_letter = get_column_letter(column[0].column)
        for cell in column:
            try:
                if cell.value:
                    cell_length = len(str(cell.value))
                    if cell_length > max_length:
                        max_length = cell_length
            except (TypeError, AttributeError):
                pass
        adjusted_width = min(max_length + 2, 50)  # Cap at 50 characters
        ws.column_dimensions[column_letter].width = adjusted_width


# ==================== Document Upload Routes ====================

@projects_bp.route('/projects/<int:project_id>/documents/upload', methods=['POST'])
@login_required
@tenant_required
def upload_document(project_id):
    """Upload a document to a project."""
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    tenant_id = get_current_tenant_id()

    # Check document limit
    current_docs = len(project.documents)
    if current_docs >= MAX_DOCUMENTS_PER_PROJECT:
        flash(_('Limite de %(max)s documentos por projeto atingido.', max=MAX_DOCUMENTS_PER_PROJECT), 'warning')
        return redirect(url_for('projects.view_project', project_id=project_id))

    if 'document' not in request.files:
        flash(_('Nenhum arquivo selecionado.'), 'danger')
        return redirect(url_for('projects.view_project', project_id=project_id))

    file = request.files['document']

    if file.filename == '':
        flash(_('Nenhum arquivo selecionado.'), 'danger')
        return redirect(url_for('projects.view_project', project_id=project_id))

    if not allowed_file(file.filename):
        flash(_('Tipo de arquivo não permitido. Use PDF, Word, Excel ou PowerPoint.'), 'danger')
        return redirect(url_for('projects.view_project', project_id=project_id))

    # Secure the filename and generate unique stored filename
    original_filename = secure_filename(file.filename)
    file_ext = get_file_extension(original_filename)
    stored_filename = f"{uuid.uuid4().hex}.{file_ext}"

    # Create tenant subfolder
    tenant_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], str(tenant_id or 'global'))
    os.makedirs(tenant_folder, exist_ok=True)

    # Save file
    file_path = os.path.join(tenant_folder, stored_filename)
    file.save(file_path)

    # Get file size
    file_size = os.path.getsize(file_path)

    # Get description
    description = request.form.get('description', '').strip()

    # Create document record
    doc = ProjectDocument(
        tenant_id=tenant_id,
        project_id=project_id,
        filename=original_filename,
        stored_filename=stored_filename,
        file_type=file_ext,
        file_size=file_size,
        description=description,
        uploaded_by_id=current_user.id
    )
    db.session.add(doc)
    db.session.commit()

    flash(_('Documento "%(name)s" enviado com sucesso!', name=original_filename), 'success')
    return redirect(url_for('projects.view_project', project_id=project_id))


@projects_bp.route('/projects/<int:project_id>/documents/<int:doc_id>/download')
@login_required
@tenant_required
def download_document(project_id, doc_id):
    """Download a project document."""
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    doc = ProjectDocument.query.get_or_404(doc_id)

    # Verify document belongs to project
    if doc.project_id != project_id:
        flash(_('Documento não encontrado.'), 'danger')
        return redirect(url_for('projects.view_project', project_id=project_id))

    # Use document's tenant_id for file path (supports superadmin access)
    tenant_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], str(doc.tenant_id or 'global'))
    file_path = os.path.join(tenant_folder, doc.stored_filename)

    if not os.path.exists(file_path):
        flash(_('Arquivo não encontrado no servidor.'), 'danger')
        return redirect(url_for('projects.view_project', project_id=project_id))

    return send_file(
        file_path,
        as_attachment=True,
        download_name=doc.filename
    )


@projects_bp.route('/projects/<int:project_id>/documents/<int:doc_id>/delete', methods=['POST'])
@login_required
@tenant_required
def delete_document(project_id, doc_id):
    """Delete a project document."""
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    doc = ProjectDocument.query.get_or_404(doc_id)

    # Verify document belongs to project
    if doc.project_id != project_id:
        flash(_('Documento não encontrado.'), 'danger')
        return redirect(url_for('projects.view_project', project_id=project_id))

    # Delete file from disk - use document's tenant_id for file path
    tenant_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], str(doc.tenant_id or 'global'))
    file_path = os.path.join(tenant_folder, doc.stored_filename)

    if os.path.exists(file_path):
        os.remove(file_path)

    # Delete database record
    filename = doc.filename
    db.session.delete(doc)
    db.session.commit()

    flash(_('Documento "%(name)s" excluído com sucesso!', name=filename), 'success')
    return redirect(url_for('projects.view_project', project_id=project_id))


# ============================================
# STAKEHOLDER MANAGEMENT
# ============================================

@projects_bp.route('/projects/<int:project_id>/stakeholders')
@login_required
@tenant_required
def list_stakeholders(project_id):
    """List all stakeholders for a project."""
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    stakeholders = ProjectStakeholder.query.filter_by(project_id=project_id).order_by(
        ProjectStakeholder.influence_level.desc(),
        ProjectStakeholder.name
    ).all()

    return render_template('projects/stakeholders/list.html',
                           project=project,
                           stakeholders=stakeholders)


@projects_bp.route('/projects/<int:project_id>/stakeholders/add', methods=['GET', 'POST'])
@login_required
@tenant_required
def add_stakeholder(project_id):
    """Add a new stakeholder to a project."""
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    if request.method == 'POST':
        stakeholder = ProjectStakeholder(
            tenant_id=project.tenant_id,
            project_id=project_id,
            name=request.form.get('name', '').strip(),
            email=request.form.get('email', '').strip() or None,
            phone=request.form.get('phone', '').strip() or None,
            organization=request.form.get('organization', '').strip() or None,
            role=request.form.get('role', '').strip(),
            influence_level=request.form.get('influence_level', 'Médio'),
            interest_level=request.form.get('interest_level', 'Médio'),
            engagement_strategy=request.form.get('engagement_strategy', ''),
            receive_briefing=request.form.get('receive_briefing') == 'on',
            receive_risk_alerts=request.form.get('receive_risk_alerts') == 'on',
            receive_financial_alerts=request.form.get('receive_financial_alerts') == 'on',
            receive_schedule_alerts=request.form.get('receive_schedule_alerts') == 'on',
            receive_quality_alerts=request.form.get('receive_quality_alerts') == 'on',
            receive_compliance_alerts=request.form.get('receive_compliance_alerts') == 'on',
            receive_status_reports=request.form.get('receive_status_reports') == 'on',
            notes=request.form.get('notes', '').strip() or None,
            created_by_id=current_user.id
        )
        db.session.add(stakeholder)
        db.session.commit()

        flash(_('Stakeholder "%(name)s" adicionado com sucesso!', name=stakeholder.name), 'success')
        return redirect(url_for('projects.list_stakeholders', project_id=project_id))

    return render_template('projects/stakeholders/form.html',
                           project=project,
                           stakeholder=None)


@projects_bp.route('/projects/<int:project_id>/stakeholders/<int:stakeholder_id>/edit', methods=['GET', 'POST'])
@login_required
@tenant_required
def edit_stakeholder(project_id, stakeholder_id):
    """Edit an existing stakeholder."""
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    stakeholder = ProjectStakeholder.query.get_or_404(stakeholder_id)
    if stakeholder.project_id != project_id:
        flash(_('Stakeholder não encontrado.'), 'danger')
        return redirect(url_for('projects.list_stakeholders', project_id=project_id))

    if request.method == 'POST':
        stakeholder.name = request.form.get('name', '').strip()
        stakeholder.email = request.form.get('email', '').strip() or None
        stakeholder.phone = request.form.get('phone', '').strip() or None
        stakeholder.organization = request.form.get('organization', '').strip() or None
        stakeholder.role = request.form.get('role', '').strip()
        stakeholder.influence_level = request.form.get('influence_level', 'Médio')
        stakeholder.interest_level = request.form.get('interest_level', 'Médio')
        stakeholder.engagement_strategy = request.form.get('engagement_strategy', '')
        stakeholder.receive_briefing = request.form.get('receive_briefing') == 'on'
        stakeholder.receive_risk_alerts = request.form.get('receive_risk_alerts') == 'on'
        stakeholder.receive_financial_alerts = request.form.get('receive_financial_alerts') == 'on'
        stakeholder.receive_schedule_alerts = request.form.get('receive_schedule_alerts') == 'on'
        stakeholder.receive_quality_alerts = request.form.get('receive_quality_alerts') == 'on'
        stakeholder.receive_compliance_alerts = request.form.get('receive_compliance_alerts') == 'on'
        stakeholder.receive_status_reports = request.form.get('receive_status_reports') == 'on'
        stakeholder.active = request.form.get('active') == 'on'
        stakeholder.notes = request.form.get('notes', '').strip() or None

        db.session.commit()
        flash(_('Stakeholder "%(name)s" atualizado com sucesso!', name=stakeholder.name), 'success')
        return redirect(url_for('projects.list_stakeholders', project_id=project_id))

    return render_template('projects/stakeholders/form.html',
                           project=project,
                           stakeholder=stakeholder)


@projects_bp.route('/projects/<int:project_id>/stakeholders/<int:stakeholder_id>/delete', methods=['POST'])
@login_required
@tenant_required
def delete_stakeholder(project_id, stakeholder_id):
    """Delete a stakeholder."""
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    stakeholder = ProjectStakeholder.query.get_or_404(stakeholder_id)
    if stakeholder.project_id != project_id:
        flash(_('Stakeholder não encontrado.'), 'danger')
        return redirect(url_for('projects.list_stakeholders', project_id=project_id))

    name = stakeholder.name
    db.session.delete(stakeholder)
    db.session.commit()

    flash(_('Stakeholder "%(name)s" excluído com sucesso!', name=name), 'success')
    return redirect(url_for('projects.list_stakeholders', project_id=project_id))


# ============================================
# TRL HISTORY
# ============================================

@projects_bp.route('/projects/<int:project_id>/trl-history')
@login_required
@tenant_required
def trl_history(project_id):
    """View TRL history for a project."""
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    history = ProjectTRLHistory.query.filter_by(project_id=project_id).order_by(
        ProjectTRLHistory.change_date.desc()
    ).all()

    return render_template('projects/trl_history.html',
                           project=project,
                           history=history)


@projects_bp.route('/projects/<int:project_id>/update-trl', methods=['POST'])
@login_required
@tenant_required
def update_trl(project_id):
    """Update TRL with history tracking."""
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    new_trl = int(request.form.get('trl', project.trl))

    if new_trl != project.trl:
        trl_history = ProjectTRLHistory(
            tenant_id=project.tenant_id,
            project_id=project.id,
            trl_from=project.trl,
            trl_to=new_trl,
            change_date=datetime.strptime(request.form.get('change_date', ''), '%Y-%m-%d').date() if request.form.get('change_date') else datetime.now().date(),
            justification=request.form.get('justification', ''),
            evidence=request.form.get('evidence', ''),
            verified_by=request.form.get('verified_by', ''),
            changed_by_id=current_user.id
        )
        db.session.add(trl_history)
        project.trl = new_trl
        db.session.commit()

        flash(_('TRL atualizado de %(from_trl)s para %(to_trl)s!', from_trl=trl_history.trl_from, to_trl=new_trl), 'success')
    else:
        flash(_('TRL não foi alterado.'), 'info')

    return redirect(url_for('projects.view_project', project_id=project_id))


# ============================================
# AI SUGGESTIONS FOR TRL AND KPIs
# ============================================

@projects_bp.route('/projects/<int:project_id>/suggest-trl-kpi', methods=['POST'])
@login_required
@tenant_required
def suggest_trl_kpi(project_id):
    """Get AI suggestions for TRL and innovation KPIs."""
    import os
    if not os.environ.get('ANTHROPIC_API_KEY'):
        return {'error': 'API de IA não configurada.'}, 400

    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    from services.ai_service import get_anthropic_client
    client = get_anthropic_client()

    # Gather project info
    milestones_info = "\n".join([f"- {m.title}: {m.progress}% ({m.status})" for m in project.milestones[:10]])
    expenses_total = sum(e.amount for e in project.expenses if e.status != 'Rejeitada')

    prompt = f"""Analise este projeto de P&D e sugira o TRL (Technology Readiness Level) atual e KPIs de inovação apropriados.

PROJETO:
- Título: {project.title}
- Descrição: {project.description or 'Não informada'}
- Categoria: {project.category or 'Não informada'}
- Status: {project.status}
- Orçamento: R$ {project.budget:,.2f}
- Gastos: R$ {expenses_total:,.2f}
- Data Início: {project.start_date}
- Data Fim: {project.end_date}

MARCOS/ATIVIDADES:
{milestones_info or 'Nenhum marco cadastrado'}

Responda APENAS em JSON válido com esta estrutura:
{{
    "trl_sugerido": <número 1-9>,
    "trl_justificativa": "<explicação breve>",
    "innovation_type": "<Radical|Incremental|Disruptiva|Arquitetural>",
    "innovation_scope": "<Produto|Processo|Modelo de Negócio|Organizacional>",
    "ip_strategy": "<Patente|Segredo Industrial|Open Source|Nenhuma>",
    "innovation_risk_level": "<Baixo|Médio|Alto|Muito Alto>",
    "time_to_market_meses": <número>,
    "expected_roi_percent": <número>,
    "target_market": "<descrição do mercado-alvo>",
    "competitive_advantage": "<vantagem competitiva esperada>"
}}

Baseie-se nos níveis TRL:
1: Princípios básicos observados
2: Conceito de tecnologia formulado
3: Prova de conceito experimental
4: Validação em laboratório
5: Validação em ambiente relevante
6: Demonstração em ambiente relevante
7: Demonstração em ambiente operacional
8: Sistema completo e qualificado
9: Sistema comprovado em operação
"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )

        import json
        response_text = response.content[0].text.strip()
        # Extract JSON from response
        if '```json' in response_text:
            response_text = response_text.split('```json')[1].split('```')[0]
        elif '```' in response_text:
            response_text = response_text.split('```')[1].split('```')[0]

        suggestion = json.loads(response_text)
        return suggestion

    except Exception as e:
        return {'error': str(e)}, 500
