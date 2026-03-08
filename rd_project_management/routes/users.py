from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from functools import wraps
from models import db, User
from services.tenant_utils import tenant_required, admin_required, get_current_tenant_id

users_bp = Blueprint('users', __name__)


def tenant_admin_required(f):
    """Decorator to require tenant admin role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))

        # Super admins can access everything
        if current_user.is_superadmin():
            return f(*args, **kwargs)

        # Tenant admins can manage users
        if current_user.role not in ['admin', 'manager']:
            flash('Acesso restrito a administradores.', 'danger')
            return redirect(url_for('projects.list_projects'))

        return f(*args, **kwargs)
    return decorated_function


@users_bp.route('/users')
@login_required
@tenant_required
@tenant_admin_required
def list_users():
    """List all users in the tenant."""
    search = request.args.get('search', '')
    role_filter = request.args.get('role', '')

    tenant_id = get_current_tenant_id()

    # Filter users by tenant
    if tenant_id:
        query = User.query.filter_by(tenant_id=tenant_id)
    else:
        # Super admin sees all non-superadmin users
        query = User.query.filter(User.role != 'superadmin')

    if search:
        query = query.filter(
            db.or_(
                User.full_name.ilike(f'%{search}%'),
                User.username.ilike(f'%{search}%'),
                User.email.ilike(f'%{search}%')
            )
        )
    if role_filter:
        query = query.filter_by(role=role_filter)

    users = query.order_by(User.full_name).all()

    # Stats for tenant
    base_query = User.query.filter_by(tenant_id=tenant_id) if tenant_id else User.query.filter(User.role != 'superadmin')
    total_users = base_query.count()
    total_admins = base_query.filter_by(role='admin').count()
    total_active = base_query.filter_by(active=True).count()

    return render_template('users/list.html',
                           users=users,
                           total_users=total_users,
                           total_admins=total_admins,
                           total_active=total_active,
                           search=search,
                           role_filter=role_filter)


@users_bp.route('/users/new', methods=['GET', 'POST'])
@login_required
@tenant_required
@tenant_admin_required
def create_user():
    """Create a new user in the tenant."""
    tenant_id = get_current_tenant_id()

    # Check user limit for tenant
    if tenant_id and current_user.tenant and not current_user.tenant.can_add_user():
        flash(f'Limite de usuários atingido ({current_user.tenant.max_users}). Entre em contato com o suporte.', 'warning')
        return redirect(url_for('users.list_users'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        full_name = request.form.get('full_name', '').strip()
        password = request.form.get('password', '')
        role = request.form.get('role', 'user')
        active = request.form.get('active') == 'on'

        # Prevent creating superadmin
        if role == 'superadmin':
            role = 'admin'

        # Validations
        if not username or not email or not full_name or not password:
            flash('Todos os campos obrigatórios devem ser preenchidos.', 'danger')
            return render_template('users/form.html', user=None)

        if len(password) < 6:
            flash('A senha deve ter pelo menos 6 caracteres.', 'danger')
            return render_template('users/form.html', user=None)

        # Check if username exists in tenant
        if tenant_id:
            existing = User.query.filter_by(tenant_id=tenant_id, username=username).first()
        else:
            existing = User.query.filter_by(username=username).first()
        if existing:
            flash('Este nome de usuário já está em uso.', 'danger')
            return render_template('users/form.html', user=None)

        # Check if email exists in tenant
        if tenant_id:
            existing = User.query.filter_by(tenant_id=tenant_id, email=email).first()
        else:
            existing = User.query.filter_by(email=email).first()
        if existing:
            flash('Este email já está cadastrado.', 'danger')
            return render_template('users/form.html', user=None)

        user = User(
            tenant_id=tenant_id,
            username=username,
            email=email,
            full_name=full_name,
            role=role,
            active=active
        )
        user.set_password(password)

        db.session.add(user)
        db.session.commit()
        flash(f'Usuário "{full_name}" criado com sucesso!', 'success')
        return redirect(url_for('users.list_users'))

    return render_template('users/form.html', user=None)


@users_bp.route('/users/<int:user_id>')
@login_required
@tenant_required
@tenant_admin_required
def view_user(user_id):
    """View user details."""
    user = User.query.get_or_404(user_id)

    # Check tenant access
    tenant_id = get_current_tenant_id()
    if tenant_id and user.tenant_id != tenant_id:
        flash('Usuário não encontrado.', 'danger')
        return redirect(url_for('users.list_users'))

    # Count user activities
    projects_count = len(user.projects) if hasattr(user, 'projects') else 0
    timesheets_count = len(user.timesheets) if hasattr(user, 'timesheets') else 0
    expenses_count = len(user.expenses) if hasattr(user, 'expenses') else 0

    return render_template('users/view.html',
                           user=user,
                           projects_count=projects_count,
                           timesheets_count=timesheets_count,
                           expenses_count=expenses_count)


@users_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@tenant_required
@tenant_admin_required
def edit_user(user_id):
    """Edit an existing user."""
    user = User.query.get_or_404(user_id)

    # Check tenant access
    tenant_id = get_current_tenant_id()
    if tenant_id and user.tenant_id != tenant_id:
        flash('Usuário não encontrado.', 'danger')
        return redirect(url_for('users.list_users'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        full_name = request.form.get('full_name', '').strip()
        password = request.form.get('password', '')
        role = request.form.get('role', user.role)
        active = request.form.get('active') == 'on'

        # Prevent changing to superadmin
        if role == 'superadmin':
            role = 'admin'

        # Validations
        if not username or not email or not full_name:
            flash('Todos os campos obrigatórios devem ser preenchidos.', 'danger')
            return render_template('users/form.html', user=user)

        # Check if username exists (excluding current user)
        if tenant_id:
            existing = User.query.filter_by(tenant_id=tenant_id, username=username).first()
        else:
            existing = User.query.filter_by(username=username).first()
        if existing and existing.id != user.id:
            flash('Este nome de usuário já está em uso.', 'danger')
            return render_template('users/form.html', user=user)

        # Check if email exists (excluding current user)
        if tenant_id:
            existing = User.query.filter_by(tenant_id=tenant_id, email=email).first()
        else:
            existing = User.query.filter_by(email=email).first()
        if existing and existing.id != user.id:
            flash('Este email já está cadastrado.', 'danger')
            return render_template('users/form.html', user=user)

        # Prevent removing the last admin in tenant
        if user.role == 'admin' and role != 'admin':
            admin_count = User.query.filter_by(tenant_id=tenant_id, role='admin').count() if tenant_id else User.query.filter_by(role='admin').count()
            if admin_count <= 1:
                flash('Não é possível remover o papel de administrador do último admin.', 'danger')
                return render_template('users/form.html', user=user)

        # Prevent deactivating self
        if user.id == current_user.id and not active:
            flash('Você não pode desativar sua própria conta.', 'danger')
            return render_template('users/form.html', user=user)

        user.username = username
        user.email = email
        user.full_name = full_name
        user.role = role
        user.active = active

        # Update password only if provided
        if password:
            if len(password) < 6:
                flash('A senha deve ter pelo menos 6 caracteres.', 'danger')
                return render_template('users/form.html', user=user)
            user.set_password(password)

        db.session.commit()
        flash(f'Usuário "{full_name}" atualizado com sucesso!', 'success')
        return redirect(url_for('users.list_users'))

    return render_template('users/form.html', user=user)


@users_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@tenant_required
@tenant_admin_required
def delete_user(user_id):
    """Delete a user."""
    user = User.query.get_or_404(user_id)

    # Check tenant access
    tenant_id = get_current_tenant_id()
    if tenant_id and user.tenant_id != tenant_id:
        flash('Usuário não encontrado.', 'danger')
        return redirect(url_for('users.list_users'))

    # Prevent deleting self
    if user.id == current_user.id:
        flash('Você não pode excluir sua própria conta.', 'danger')
        return redirect(url_for('users.list_users'))

    # Prevent deleting the last admin
    if user.role == 'admin':
        admin_count = User.query.filter_by(tenant_id=tenant_id, role='admin').count() if tenant_id else User.query.filter_by(role='admin').count()
        if admin_count <= 1:
            flash('Não é possível excluir o último administrador.', 'danger')
            return redirect(url_for('users.list_users'))

    # Check if user has related data
    has_data = (
        len(user.timesheets) > 0 or
        len(user.expenses) > 0 or
        len(user.projects) > 0
    )

    if has_data:
        flash('Este usuário possui dados vinculados (timesheets, despesas ou projetos). '
              'Desative o usuário ao invés de excluir.', 'warning')
        return redirect(url_for('users.list_users'))

    db.session.delete(user)
    db.session.commit()
    flash(f'Usuário "{user.full_name}" excluído com sucesso!', 'success')
    return redirect(url_for('users.list_users'))


@users_bp.route('/users/<int:user_id>/toggle-active', methods=['POST'])
@login_required
@tenant_required
@tenant_admin_required
def toggle_active(user_id):
    """Toggle user active status."""
    user = User.query.get_or_404(user_id)

    # Check tenant access
    tenant_id = get_current_tenant_id()
    if tenant_id and user.tenant_id != tenant_id:
        flash('Usuário não encontrado.', 'danger')
        return redirect(url_for('users.list_users'))

    # Prevent deactivating self
    if user.id == current_user.id:
        flash('Você não pode desativar sua própria conta.', 'danger')
        return redirect(url_for('users.list_users'))

    user.active = not user.active
    db.session.commit()

    status = 'ativado' if user.active else 'desativado'
    flash(f'Usuário "{user.full_name}" {status} com sucesso!', 'success')
    return redirect(url_for('users.list_users'))


@users_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User's own profile page."""
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not full_name or not email:
            flash('Nome e email são obrigatórios.', 'danger')
            return render_template('users/profile.html')

        # Check if email exists (excluding current user, within tenant)
        tenant_id = get_current_tenant_id()
        if tenant_id:
            existing = User.query.filter_by(tenant_id=tenant_id, email=email).first()
        else:
            existing = User.query.filter_by(email=email).first()
        if existing and existing.id != current_user.id:
            flash('Este email já está cadastrado.', 'danger')
            return render_template('users/profile.html')

        current_user.full_name = full_name
        current_user.email = email

        # Change password if provided
        if new_password:
            if not current_user.check_password(current_password):
                flash('Senha atual incorreta.', 'danger')
                return render_template('users/profile.html')
            if len(new_password) < 6:
                flash('A nova senha deve ter pelo menos 6 caracteres.', 'danger')
                return render_template('users/profile.html')
            if new_password != confirm_password:
                flash('A confirmação da nova senha não confere.', 'danger')
                return render_template('users/profile.html')
            current_user.set_password(new_password)
            flash('Senha alterada com sucesso!', 'success')

        db.session.commit()
        flash('Perfil atualizado com sucesso!', 'success')
        return redirect(url_for('users.profile'))

    return render_template('users/profile.html')
