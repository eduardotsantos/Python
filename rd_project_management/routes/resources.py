from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from models import db, Resource, Project
from services.tenant_utils import tenant_required, ensure_tenant_access, get_current_tenant_id
from datetime import datetime

resources_bp = Blueprint('resources', __name__)


@resources_bp.route('/projects/<int:project_id>/resources')
@login_required
@tenant_required
def list_resources(project_id):
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    type_filter = request.args.get('type', '')

    query = Resource.query.filter_by(project_id=project_id)
    if type_filter:
        query = query.filter_by(type=type_filter)

    resources = query.order_by(Resource.type, Resource.name).all()
    people = [r for r in resources if r.type == 'Pessoa']
    machines = [r for r in resources if r.type == 'Máquina']
    total_cost = sum(r.hours_allocated * r.hourly_cost for r in resources)

    return render_template('resources/list.html',
                           project=project,
                           resources=resources,
                           people=people,
                           machines=machines,
                           total_cost=total_cost,
                           type_filter=type_filter)


@resources_bp.route('/projects/<int:project_id>/resources/new', methods=['GET', 'POST'])
@login_required
@tenant_required
def create_resource(project_id):
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    tenant_id = get_current_tenant_id()

    if request.method == 'POST':
        resource = Resource(
            tenant_id=tenant_id,
            project_id=project_id,
            type=request.form.get('type', 'Pessoa'),
            name=request.form.get('name', '').strip(),
            role=request.form.get('role', '').strip(),
            hours_allocated=float(request.form.get('hours_allocated', 0) or 0),
            hourly_cost=float(request.form.get('hourly_cost', 0) or 0),
            status=request.form.get('status', 'Ativo'),
            notes=request.form.get('notes', '').strip()
        )
        start_date_str = request.form.get('start_date', '')
        end_date_str = request.form.get('end_date', '')
        if start_date_str:
            resource.start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        if end_date_str:
            resource.end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

        db.session.add(resource)
        db.session.commit()
        flash('Recurso adicionado com sucesso!', 'success')
        return redirect(url_for('resources.list_resources', project_id=project_id))

    return render_template('resources/form.html', project=project, resource=None)


@resources_bp.route('/projects/<int:project_id>/resources/<int:resource_id>/edit', methods=['GET', 'POST'])
@login_required
@tenant_required
def edit_resource(project_id, resource_id):
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    resource = Resource.query.get_or_404(resource_id)
    ensure_tenant_access(resource)

    if request.method == 'POST':
        resource.type = request.form.get('type', 'Pessoa')
        resource.name = request.form.get('name', '').strip()
        resource.role = request.form.get('role', '').strip()
        resource.hours_allocated = float(request.form.get('hours_allocated', 0) or 0)
        resource.hourly_cost = float(request.form.get('hourly_cost', 0) or 0)
        resource.status = request.form.get('status', 'Ativo')
        resource.notes = request.form.get('notes', '').strip()

        start_date_str = request.form.get('start_date', '')
        end_date_str = request.form.get('end_date', '')
        if start_date_str:
            resource.start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        if end_date_str:
            resource.end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

        db.session.commit()
        flash('Recurso atualizado com sucesso!', 'success')
        return redirect(url_for('resources.list_resources', project_id=project_id))

    return render_template('resources/form.html', project=project, resource=resource)


@resources_bp.route('/projects/<int:project_id>/resources/<int:resource_id>/delete', methods=['POST'])
@login_required
@tenant_required
def delete_resource(project_id, resource_id):
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    resource = Resource.query.get_or_404(resource_id)
    ensure_tenant_access(resource)

    db.session.delete(resource)
    db.session.commit()
    flash('Recurso excluído com sucesso!', 'success')
    return redirect(url_for('resources.list_resources', project_id=project_id))
