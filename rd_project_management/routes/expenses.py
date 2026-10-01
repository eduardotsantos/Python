from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, send_file
from flask_login import login_required, current_user
from models import db, Expense, Project, ExpenseAttachment
from services.tenant_utils import tenant_required, ensure_tenant_access, get_current_tenant_id
from werkzeug.utils import secure_filename
from datetime import datetime
import uuid
import os

expenses_bp = Blueprint('expenses', __name__)

ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx'}
MAX_ATTACHMENTS_PER_EXPENSE = 5


def allowed_file(filename):
    """Check if file extension is allowed."""
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in ALLOWED_EXTENSIONS


def get_file_extension(filename):
    """Get file extension."""
    if '.' in filename:
        return filename.rsplit('.', 1)[1].lower()
    return ''


@expenses_bp.route('/projects/<int:project_id>/expenses')
@login_required
@tenant_required
def list_expenses(project_id):
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    category_filter = request.args.get('category', '')
    status_filter = request.args.get('status', '')

    query = Expense.query.filter_by(project_id=project_id)
    if category_filter:
        query = query.filter_by(category=category_filter)
    if status_filter:
        query = query.filter_by(status=status_filter)

    expenses = query.order_by(Expense.date.desc()).all()
    total = sum(e.amount for e in expenses)
    total_approved = sum(e.amount for e in expenses if e.status == 'Aprovada')
    total_pending = sum(e.amount for e in expenses if e.status == 'Pendente')

    return render_template('expenses/list.html',
                           project=project,
                           expenses=expenses,
                           total=total,
                           total_approved=total_approved,
                           total_pending=total_pending,
                           category_filter=category_filter,
                           status_filter=status_filter)


@expenses_bp.route('/projects/<int:project_id>/expenses/new', methods=['GET', 'POST'])
@login_required
@tenant_required
def create_expense(project_id):
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    tenant_id = get_current_tenant_id()

    if request.method == 'POST':
        expense = Expense(
            tenant_id=tenant_id,
            project_id=project_id,
            description=request.form.get('description', '').strip(),
            category=request.form.get('category', ''),
            amount=float(request.form.get('amount', 0)),
            date=datetime.strptime(request.form.get('date', ''), '%Y-%m-%d').date() if request.form.get('date') else datetime.today().date(),
            receipt_number=request.form.get('receipt_number', '').strip(),
            supplier=request.form.get('supplier', '').strip(),
            status=request.form.get('status', 'Pendente'),
            notes=request.form.get('notes', '').strip(),
            created_by_id=current_user.id
        )
        db.session.add(expense)
        db.session.commit()
        flash('Despesa adicionada com sucesso!', 'success')
        return redirect(url_for('expenses.list_expenses', project_id=project_id))

    return render_template('expenses/form.html', project=project, expense=None)


@expenses_bp.route('/projects/<int:project_id>/expenses/<int:expense_id>/edit', methods=['GET', 'POST'])
@login_required
@tenant_required
def edit_expense(project_id, expense_id):
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    expense = Expense.query.get_or_404(expense_id)
    ensure_tenant_access(expense)

    if request.method == 'POST':
        expense.description = request.form.get('description', '').strip()
        expense.category = request.form.get('category', '')
        expense.amount = float(request.form.get('amount', 0))
        expense.date = datetime.strptime(request.form.get('date', ''), '%Y-%m-%d').date() if request.form.get('date') else expense.date
        expense.receipt_number = request.form.get('receipt_number', '').strip()
        expense.supplier = request.form.get('supplier', '').strip()
        expense.status = request.form.get('status', 'Pendente')
        expense.notes = request.form.get('notes', '').strip()

        db.session.commit()
        flash('Despesa atualizada com sucesso!', 'success')
        return redirect(url_for('expenses.list_expenses', project_id=project_id))

    return render_template('expenses/form.html', project=project, expense=expense)


@expenses_bp.route('/projects/<int:project_id>/expenses/<int:expense_id>/delete', methods=['POST'])
@login_required
@tenant_required
def delete_expense(project_id, expense_id):
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    expense = Expense.query.get_or_404(expense_id)
    ensure_tenant_access(expense)

    db.session.delete(expense)
    db.session.commit()
    flash('Despesa excluída com sucesso!', 'success')
    return redirect(url_for('expenses.list_expenses', project_id=project_id))


@expenses_bp.route('/projects/<int:project_id>/expenses/<int:expense_id>/attachments/upload', methods=['POST'])
@login_required
@tenant_required
def upload_attachment(project_id, expense_id):
    """Upload an attachment to an expense."""
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    expense = Expense.query.get_or_404(expense_id)
    ensure_tenant_access(expense)

    tenant_id = get_current_tenant_id()

    current_attachments = len(expense.attachments)
    if current_attachments >= MAX_ATTACHMENTS_PER_EXPENSE:
        flash(f'Limite de {MAX_ATTACHMENTS_PER_EXPENSE} anexos por despesa atingido.', 'warning')
        return redirect(url_for('expenses.edit_expense', project_id=project_id, expense_id=expense_id))

    if 'attachment' not in request.files:
        flash('Nenhum arquivo selecionado.', 'danger')
        return redirect(url_for('expenses.edit_expense', project_id=project_id, expense_id=expense_id))

    file = request.files['attachment']
    attachment_type = request.form.get('attachment_type', 'comprovante')

    if file.filename == '':
        flash('Nenhum arquivo selecionado.', 'danger')
        return redirect(url_for('expenses.edit_expense', project_id=project_id, expense_id=expense_id))

    if not allowed_file(file.filename):
        flash('Tipo de arquivo não permitido. Use PDF, JPG, PNG ou Word.', 'danger')
        return redirect(url_for('expenses.edit_expense', project_id=project_id, expense_id=expense_id))

    original_filename = secure_filename(file.filename)
    file_ext = get_file_extension(original_filename)
    stored_filename = f"expense_{uuid.uuid4().hex}.{file_ext}"

    tenant_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], str(tenant_id or 'global'), 'expenses')
    os.makedirs(tenant_folder, exist_ok=True)

    file_path = os.path.join(tenant_folder, stored_filename)
    file.save(file_path)

    file_size = os.path.getsize(file_path)

    attachment = ExpenseAttachment(
        tenant_id=tenant_id,
        expense_id=expense_id,
        filename=original_filename,
        stored_filename=stored_filename,
        file_type=file_ext,
        file_size=file_size,
        attachment_type=attachment_type,
        uploaded_by_id=current_user.id
    )
    db.session.add(attachment)
    db.session.commit()

    type_names = {'boleto': 'Boleto', 'nota_fiscal': 'Nota Fiscal', 'comprovante': 'Comprovante'}
    flash(f'{type_names.get(attachment_type, "Anexo")} enviado com sucesso!', 'success')
    return redirect(url_for('expenses.edit_expense', project_id=project_id, expense_id=expense_id))


@expenses_bp.route('/projects/<int:project_id>/expenses/<int:expense_id>/attachments/<int:attachment_id>/download')
@login_required
@tenant_required
def download_attachment(project_id, expense_id, attachment_id):
    """Download an expense attachment."""
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    expense = Expense.query.get_or_404(expense_id)
    ensure_tenant_access(expense)

    attachment = ExpenseAttachment.query.get_or_404(attachment_id)

    if attachment.expense_id != expense_id:
        flash('Anexo não encontrado.', 'danger')
        return redirect(url_for('expenses.edit_expense', project_id=project_id, expense_id=expense_id))

    tenant_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], str(attachment.tenant_id or 'global'), 'expenses')
    file_path = os.path.join(tenant_folder, attachment.stored_filename)

    if not os.path.exists(file_path):
        flash('Arquivo não encontrado no servidor.', 'danger')
        return redirect(url_for('expenses.edit_expense', project_id=project_id, expense_id=expense_id))

    return send_file(file_path, download_name=attachment.filename, as_attachment=True)


@expenses_bp.route('/projects/<int:project_id>/expenses/<int:expense_id>/attachments/<int:attachment_id>/delete', methods=['POST'])
@login_required
@tenant_required
def delete_attachment(project_id, expense_id, attachment_id):
    """Delete an expense attachment."""
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    expense = Expense.query.get_or_404(expense_id)
    ensure_tenant_access(expense)

    attachment = ExpenseAttachment.query.get_or_404(attachment_id)

    if attachment.expense_id != expense_id:
        flash('Anexo não encontrado.', 'danger')
        return redirect(url_for('expenses.edit_expense', project_id=project_id, expense_id=expense_id))

    tenant_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], str(attachment.tenant_id or 'global'), 'expenses')
    file_path = os.path.join(tenant_folder, attachment.stored_filename)

    if os.path.exists(file_path):
        os.remove(file_path)

    db.session.delete(attachment)
    db.session.commit()

    flash('Anexo excluído com sucesso!', 'success')
    return redirect(url_for('expenses.edit_expense', project_id=project_id, expense_id=expense_id))
