from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, Expense, Project
from datetime import datetime

expenses_bp = Blueprint('expenses', __name__)


@expenses_bp.route('/projects/<int:project_id>/expenses')
@login_required
def list_expenses(project_id):
    project = Project.query.get_or_404(project_id)
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
def create_expense(project_id):
    project = Project.query.get_or_404(project_id)

    if request.method == 'POST':
        expense = Expense(
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
def edit_expense(project_id, expense_id):
    project = Project.query.get_or_404(project_id)
    expense = Expense.query.get_or_404(expense_id)

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
def delete_expense(project_id, expense_id):
    expense = Expense.query.get_or_404(expense_id)
    db.session.delete(expense)
    db.session.commit()
    flash('Despesa excluída com sucesso!', 'success')
    return redirect(url_for('expenses.list_expenses', project_id=project_id))
