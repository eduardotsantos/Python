"""
Tenant management routes for super admins.
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from flask_babel import _
from models import db, Tenant, User, Project
from services.tenant_utils import superadmin_required
from datetime import datetime, date, timedelta
import re

tenants_bp = Blueprint('tenants', __name__)


def slugify(text):
    """Convert text to URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r'[àáâãäå]', 'a', text)
    text = re.sub(r'[èéêë]', 'e', text)
    text = re.sub(r'[ìíîï]', 'i', text)
    text = re.sub(r'[òóôõö]', 'o', text)
    text = re.sub(r'[ùúûü]', 'u', text)
    text = re.sub(r'[ç]', 'c', text)
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-')


@tenants_bp.route('/admin/tenants')
@login_required
@superadmin_required
def list_tenants():
    """List all tenants."""
    tenants = Tenant.query.order_by(Tenant.name).all()

    # Get stats for each tenant
    tenant_stats = {}
    for tenant in tenants:
        tenant_stats[tenant.id] = {
            'users': User.query.filter_by(tenant_id=tenant.id).count(),
            'projects': Project.query.filter_by(tenant_id=tenant.id).count()
        }

    return render_template('tenants/list.html',
                           tenants=tenants,
                           tenant_stats=tenant_stats,
                           today=date.today())


@tenants_bp.route('/admin/tenants/new', methods=['GET', 'POST'])
@login_required
@superadmin_required
def create_tenant():
    """Create a new tenant."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        slug = request.form.get('slug', '').strip() or slugify(name)
        cnpj = request.form.get('cnpj', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        state = request.form.get('state', '').strip()
        municipality = request.form.get('municipality', '').strip()
        plan = request.form.get('plan', 'basic')
        max_users = int(request.form.get('max_users', 5))
        max_projects = int(request.form.get('max_projects', 10))
        expires_at_str = request.form.get('expires_at', '')

        # Validate
        if not name:
            flash(_('Nome da empresa é obrigatório.'), 'danger')
            return render_template('tenants/form.html', tenant=None)

        # Check if slug is unique
        existing = Tenant.query.filter_by(slug=slug).first()
        if existing:
            flash(_('Já existe uma empresa com este identificador.'), 'danger')
            return render_template('tenants/form.html', tenant=None)

        # Parse expiration date
        expires_at = None
        if expires_at_str:
            try:
                expires_at = datetime.strptime(expires_at_str, '%Y-%m-%d').date()
            except ValueError:
                pass

        # Email configuration
        email_enabled = request.form.get('email_enabled') == 'on'
        mail_server = request.form.get('mail_server', '').strip()
        mail_port_str = request.form.get('mail_port', '587').strip()
        mail_port = int(mail_port_str) if mail_port_str else 587

        mail_security = request.form.get('mail_security', 'tls')
        mail_use_tls = (mail_security == 'tls')
        mail_use_ssl = (mail_security == 'ssl')

        mail_username = request.form.get('mail_username', '').strip()
        mail_password = request.form.get('mail_password', '').strip()
        mail_default_sender = request.form.get('mail_default_sender', '').strip()

        # Create tenant
        tenant = Tenant(
            name=name,
            slug=slug,
            cnpj=cnpj,
            email=email,
            phone=phone,
            address=address,
            state=state,
            municipality=municipality,
            plan=plan,
            max_users=max_users,
            max_projects=max_projects,
            expires_at=expires_at,
            active=True,
            email_enabled=email_enabled,
            mail_server=mail_server,
            mail_port=mail_port,
            mail_use_tls=mail_use_tls,
            mail_use_ssl=mail_use_ssl,
            mail_username=mail_username,
            mail_password=mail_password,
            mail_default_sender=mail_default_sender
        )
        db.session.add(tenant)
        db.session.commit()

        # Create admin user for the tenant
        admin_email = request.form.get('admin_email', '').strip()
        admin_name = request.form.get('admin_name', '').strip()
        admin_password = request.form.get('admin_password', '').strip()

        if admin_email and admin_name and admin_password:
            admin_user = User(
                tenant_id=tenant.id,
                username=admin_email.split('@')[0],
                email=admin_email,
                full_name=admin_name,
                role='admin',
                active=True
            )
            admin_user.set_password(admin_password)
            db.session.add(admin_user)
            db.session.commit()
            flash(_('Empresa "%(name)s" e usuário administrador criados com sucesso!', name=name), 'success')
        else:
            flash(_('Empresa "%(name)s" criada com sucesso!', name=name), 'success')

        return redirect(url_for('tenants.list_tenants'))

    return render_template('tenants/form.html', tenant=None)


@tenants_bp.route('/admin/tenants/<int:tenant_id>')
@login_required
@superadmin_required
def view_tenant(tenant_id):
    """View tenant details."""
    tenant = Tenant.query.get_or_404(tenant_id)
    users = User.query.filter_by(tenant_id=tenant_id).order_by(User.full_name).all()
    projects = Project.query.filter_by(tenant_id=tenant_id).order_by(Project.title).all()

    return render_template('tenants/view.html',
                           tenant=tenant,
                           users=users,
                           projects=projects)


@tenants_bp.route('/admin/tenants/<int:tenant_id>/edit', methods=['GET', 'POST'])
@login_required
@superadmin_required
def edit_tenant(tenant_id):
    """Edit a tenant."""
    tenant = Tenant.query.get_or_404(tenant_id)

    if request.method == 'POST':
        tenant.name = request.form.get('name', '').strip() or tenant.name
        new_slug = request.form.get('slug', '').strip()

        # Check slug uniqueness if changed
        if new_slug and new_slug != tenant.slug:
            existing = Tenant.query.filter_by(slug=new_slug).first()
            if existing:
                flash(_('Já existe uma empresa com este identificador.'), 'danger')
                return render_template('tenants/form.html', tenant=tenant)
            tenant.slug = new_slug

        tenant.cnpj = request.form.get('cnpj', '').strip()
        tenant.email = request.form.get('email', '').strip()
        tenant.phone = request.form.get('phone', '').strip()
        tenant.address = request.form.get('address', '').strip()
        tenant.state = request.form.get('state', '').strip()
        tenant.municipality = request.form.get('municipality', '').strip()
        tenant.plan = request.form.get('plan', tenant.plan)
        tenant.max_users = int(request.form.get('max_users', tenant.max_users))
        tenant.max_projects = int(request.form.get('max_projects', tenant.max_projects))
        tenant.active = request.form.get('active') == 'on'

        expires_at_str = request.form.get('expires_at', '')
        if expires_at_str:
            try:
                tenant.expires_at = datetime.strptime(expires_at_str, '%Y-%m-%d').date()
            except ValueError:
                pass
        else:
            tenant.expires_at = None

        # Email configuration
        tenant.email_enabled = request.form.get('email_enabled') == 'on'
        tenant.mail_server = request.form.get('mail_server', '').strip()
        mail_port = request.form.get('mail_port', '587').strip()
        tenant.mail_port = int(mail_port) if mail_port else 587

        mail_security = request.form.get('mail_security', 'tls')
        tenant.mail_use_tls = (mail_security == 'tls')
        tenant.mail_use_ssl = (mail_security == 'ssl')

        tenant.mail_username = request.form.get('mail_username', '').strip()
        mail_password = request.form.get('mail_password', '').strip()
        if mail_password:
            tenant.mail_password = mail_password
        tenant.mail_default_sender = request.form.get('mail_default_sender', '').strip()

        db.session.commit()
        flash(_('Empresa atualizada com sucesso!'), 'success')
        return redirect(url_for('tenants.view_tenant', tenant_id=tenant_id))

    return render_template('tenants/form.html', tenant=tenant)


@tenants_bp.route('/admin/tenants/<int:tenant_id>/delete', methods=['POST'])
@login_required
@superadmin_required
def delete_tenant(tenant_id):
    """Delete a tenant and all its data."""
    tenant = Tenant.query.get_or_404(tenant_id)

    # Check if tenant has data
    user_count = User.query.filter_by(tenant_id=tenant_id).count()
    project_count = Project.query.filter_by(tenant_id=tenant_id).count()

    if user_count > 0 or project_count > 0:
        flash(_('Não é possível excluir a empresa "%(name)s". Ela possui %(users)s usuários e %(projects)s projetos. Remova os dados primeiro.', name=tenant.name, users=user_count, projects=project_count), 'danger')
        return redirect(url_for('tenants.view_tenant', tenant_id=tenant_id))

    db.session.delete(tenant)
    db.session.commit()
    flash(_('Empresa "%(name)s" excluída com sucesso!', name=tenant.name), 'success')
    return redirect(url_for('tenants.list_tenants'))


@tenants_bp.route('/admin/tenants/<int:tenant_id>/toggle-status', methods=['POST'])
@login_required
@superadmin_required
def toggle_tenant_status(tenant_id):
    """Toggle tenant active status."""
    tenant = Tenant.query.get_or_404(tenant_id)
    tenant.active = not tenant.active
    db.session.commit()

    status = 'ativada' if tenant.active else 'desativada'
    flash(_('Empresa "%(name)s" %(status)s com sucesso!', name=tenant.name, status=status), 'success')
    return redirect(url_for('tenants.view_tenant', tenant_id=tenant_id))


@tenants_bp.route('/admin/tenants/<int:tenant_id>/renew', methods=['POST'])
@login_required
@superadmin_required
def renew_tenant(tenant_id):
    """Renew tenant subscription."""
    tenant = Tenant.query.get_or_404(tenant_id)
    months = int(request.form.get('months', 12))

    # Calculate new expiration
    if tenant.expires_at and tenant.expires_at > date.today():
        new_date = tenant.expires_at + timedelta(days=30 * months)
    else:
        new_date = date.today() + timedelta(days=30 * months)

    tenant.expires_at = new_date
    tenant.active = True
    db.session.commit()

    flash(_('Licença renovada até %(date)s!', date=new_date.strftime('%d/%m/%Y')), 'success')
    return redirect(url_for('tenants.view_tenant', tenant_id=tenant_id))


@tenants_bp.route('/admin/tenants/<int:tenant_id>/add-user', methods=['POST'])
@login_required
@superadmin_required
def add_tenant_user(tenant_id):
    """Add a user to a tenant."""
    tenant = Tenant.query.get_or_404(tenant_id)

    if not tenant.can_add_user():
        flash(_('Limite de %(max)s usuários atingido para esta empresa.', max=tenant.max_users), 'danger')
        return redirect(url_for('tenants.view_tenant', tenant_id=tenant_id))

    email = request.form.get('email', '').strip()
    full_name = request.form.get('full_name', '').strip()
    password = request.form.get('password', '').strip()
    role = request.form.get('role', 'user')

    if not email or not full_name or not password:
        flash(_('Todos os campos são obrigatórios.'), 'danger')
        return redirect(url_for('tenants.view_tenant', tenant_id=tenant_id))

    # Check if email exists in this tenant
    existing = User.query.filter_by(tenant_id=tenant_id, email=email).first()
    if existing:
        flash(_('Já existe um usuário com este e-mail nesta empresa.'), 'danger')
        return redirect(url_for('tenants.view_tenant', tenant_id=tenant_id))

    user = User(
        tenant_id=tenant_id,
        username=email.split('@')[0],
        email=email,
        full_name=full_name,
        role=role,
        active=True
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    flash(_('Usuário "%(name)s" criado com sucesso!', name=full_name), 'success')
    return redirect(url_for('tenants.view_tenant', tenant_id=tenant_id))
