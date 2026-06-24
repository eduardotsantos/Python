"""Audit routes for viewing system audit logs."""
from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from flask_babel import _
from models import db, AuditLog, User

audit_bp = Blueprint('audit', __name__)


@audit_bp.route('/audit')
@login_required
def audit_logs():
    """View audit logs."""
    if current_user.role not in ['admin'] and not current_user.is_superadmin():
        from flask import flash, redirect, url_for
        flash(_('Acesso negado. Apenas administradores podem visualizar logs de auditoria.'), 'danger')
        return redirect(url_for('home.dashboard'))

    page = request.args.get('page', 1, type=int)
    per_page = 50

    action_filter = request.args.get('action', '')
    entity_filter = request.args.get('entity', '')
    user_filter = request.args.get('user_id', '', type=int) if request.args.get('user_id') else None

    query = AuditLog.query

    if current_user.is_superadmin():
        tenant_filter = request.args.get('tenant_id', '', type=int) if request.args.get('tenant_id') else None
        if tenant_filter:
            query = query.filter(AuditLog.tenant_id == tenant_filter)
    else:
        query = query.filter(AuditLog.tenant_id == current_user.tenant_id)

    if action_filter:
        query = query.filter(AuditLog.action == action_filter)

    if entity_filter:
        query = query.filter(AuditLog.entity_type == entity_filter)

    if user_filter:
        query = query.filter(AuditLog.user_id == user_filter)

    logs = query.order_by(AuditLog.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    if current_user.is_superadmin():
        users = User.query.order_by(User.full_name).all()
    else:
        users = User.query.filter_by(tenant_id=current_user.tenant_id).order_by(User.full_name).all()

    actions = db.session.query(AuditLog.action).distinct().all()
    actions = [a[0] for a in actions if a[0]]

    entities = db.session.query(AuditLog.entity_type).distinct().all()
    entities = [e[0] for e in entities if e[0]]

    return render_template('audit/logs.html',
                          logs=logs,
                          users=users,
                          actions=actions,
                          entities=entities,
                          action_filter=action_filter,
                          entity_filter=entity_filter,
                          user_filter=user_filter)
