"""
Tenant utilities for multi-tenancy support.
Provides decorators and helper functions for tenant isolation.
"""
from functools import wraps
from flask import g, abort, redirect, url_for, flash
from flask_login import current_user


def get_current_tenant():
    """Get the current tenant object."""
    if hasattr(g, 'current_tenant'):
        return g.current_tenant
    return None


def get_current_tenant_id():
    """Get the current tenant ID."""
    if current_user.is_authenticated:
        return current_user.tenant_id
    return None


def set_current_tenant(tenant):
    """Set the current tenant in the request context."""
    g.current_tenant = tenant


def tenant_required(f):
    """Decorator to ensure user belongs to a tenant."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))

        # Super admins bypass tenant check
        if current_user.is_superadmin():
            return f(*args, **kwargs)

        if not current_user.tenant_id:
            flash('Usuário não está associado a nenhuma empresa.', 'danger')
            return redirect(url_for('auth.logout'))

        # Check if tenant is active
        tenant = current_user.tenant
        if not tenant or not tenant.is_active():
            flash('Sua empresa está com a licença expirada ou inativa. Entre em contato com o suporte.', 'danger')
            return redirect(url_for('auth.logout'))

        set_current_tenant(tenant)
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorator to ensure user is a tenant admin."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))

        if current_user.is_superadmin():
            return f(*args, **kwargs)

        if current_user.role not in ['admin', 'manager']:
            flash('Você não tem permissão para acessar esta área.', 'danger')
            return redirect(url_for('projects.list_projects'))

        return f(*args, **kwargs)
    return decorated_function


def superadmin_required(f):
    """Decorator to ensure user is a super admin."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))

        if not current_user.is_superadmin():
            flash('Acesso restrito a administradores do sistema.', 'danger')
            return redirect(url_for('projects.list_projects'))

        return f(*args, **kwargs)
    return decorated_function


def filter_by_tenant(query, model):
    """Filter a query by the current tenant."""
    tenant_id = get_current_tenant_id()
    if tenant_id and hasattr(model, 'tenant_id'):
        return query.filter(model.tenant_id == tenant_id)
    return query


def check_tenant_access(obj):
    """Check if current user has access to an object."""
    if current_user.is_superadmin():
        return True

    tenant_id = get_current_tenant_id()
    if not tenant_id:
        return False

    if hasattr(obj, 'tenant_id'):
        return obj.tenant_id == tenant_id

    return True


def ensure_tenant_access(obj):
    """Abort with 404 if user doesn't have access to the object."""
    if not check_tenant_access(obj):
        abort(404)


class TenantQuery:
    """Mixin class to add tenant filtering to queries."""

    @staticmethod
    def for_tenant(query, model):
        """Apply tenant filter to a query."""
        return filter_by_tenant(query, model)
