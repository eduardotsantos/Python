"""
Audit routes for viewing system logs.
Available only to tenant admins.
"""
from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from models import db, AuditLog
from services.tenant_utils import tenant_required, get_current_tenant_id
from datetime import datetime, timedelta

audit_bp = Blueprint('audit', __name__)


@audit_bp.route('/audit')
@login_required
@tenant_required
def audit_logs():
    """View audit logs for the current tenant."""
    # Only admins can view audit logs
    if current_user.role not in ['admin', 'superadmin']:
        from flask import flash, redirect, url_for
        flash('Acesso negado. Apenas administradores podem ver logs de auditoria.', 'danger')
        return redirect(url_for('home.dashboard'))

    tenant_id = get_current_tenant_id()

    # Filters
    action_filter = request.args.get('action', '')
    entity_filter = request.args.get('entity', '')
    user_filter = request.args.get('user_id', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')

    # Base query - filter by tenant
    if current_user.is_superadmin():
        query = AuditLog.query
    else:
        query = AuditLog.query.filter_by(tenant_id=tenant_id)

    # Apply filters
    if action_filter:
        query = query.filter(AuditLog.action == action_filter)

    if entity_filter:
        query = query.filter(AuditLog.entity_type == entity_filter)

    if user_filter:
        query = query.filter(AuditLog.user_id == int(user_filter))

    if date_from:
        try:
            date_from_dt = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(AuditLog.created_at >= date_from_dt)
        except ValueError:
            pass

    if date_to:
        try:
            date_to_dt = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(AuditLog.created_at < date_to_dt)
        except ValueError:
            pass

    # Get logs ordered by date
    logs = query.order_by(AuditLog.created_at.desc()).limit(500).all()

    # Get unique actions and entities for filters
    if current_user.is_superadmin():
        actions = db.session.query(AuditLog.action).distinct().all()
        entities = db.session.query(AuditLog.entity_type).filter(AuditLog.entity_type.isnot(None)).distinct().all()
    else:
        actions = db.session.query(AuditLog.action).filter_by(tenant_id=tenant_id).distinct().all()
        entities = db.session.query(AuditLog.entity_type).filter_by(tenant_id=tenant_id).filter(AuditLog.entity_type.isnot(None)).distinct().all()

    actions = [a[0] for a in actions]
    entities = [e[0] for e in entities if e[0]]

    # Get users for filter
    from models import User
    if current_user.is_superadmin():
        users = User.query.order_by(User.full_name).all()
    else:
        users = User.query.filter_by(tenant_id=tenant_id).order_by(User.full_name).all()

    # Stats
    today = datetime.utcnow().date()
    if current_user.is_superadmin():
        stats = {
            'total': AuditLog.query.count(),
            'today': AuditLog.query.filter(AuditLog.created_at >= datetime.combine(today, datetime.min.time())).count(),
            'logins': AuditLog.query.filter_by(action='login').count(),
            'changes': AuditLog.query.filter(AuditLog.action.in_(['create', 'update', 'delete'])).count(),
        }
    else:
        stats = {
            'total': AuditLog.query.filter_by(tenant_id=tenant_id).count(),
            'today': AuditLog.query.filter_by(tenant_id=tenant_id).filter(AuditLog.created_at >= datetime.combine(today, datetime.min.time())).count(),
            'logins': AuditLog.query.filter_by(tenant_id=tenant_id, action='login').count(),
            'changes': AuditLog.query.filter_by(tenant_id=tenant_id).filter(AuditLog.action.in_(['create', 'update', 'delete'])).count(),
        }

    return render_template('audit/list.html',
                           logs=logs,
                           actions=actions,
                           entities=entities,
                           users=users,
                           stats=stats,
                           action_filter=action_filter,
                           entity_filter=entity_filter,
                           user_filter=user_filter,
                           date_from=date_from,
                           date_to=date_to)
