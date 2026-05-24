from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, send_file, Response
from flask_login import login_required
from models import db, Milestone, Project, User, Resource
from services.tenant_utils import tenant_required, ensure_tenant_access, get_current_tenant_id
from datetime import datetime
import xml.etree.ElementTree as ET
from io import BytesIO

schedule_bp = Blueprint('schedule', __name__)


@schedule_bp.route('/projects/<int:project_id>/schedule')
@login_required
@tenant_required
def view_schedule(project_id):
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    milestones = Milestone.query.filter_by(project_id=project_id).order_by(Milestone.order, Milestone.start_date).all()
    return render_template('schedule/view.html', project=project, milestones=milestones)


@schedule_bp.route('/projects/<int:project_id>/schedule/new', methods=['GET', 'POST'])
@login_required
@tenant_required
def create_milestone(project_id):
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    tenant_id = get_current_tenant_id()

    if request.method == 'POST':
        responsible_id = request.form.get('responsible_id')
        milestone = Milestone(
            tenant_id=tenant_id,
            project_id=project_id,
            title=request.form.get('title', '').strip(),
            description=request.form.get('description', '').strip(),
            start_date=datetime.strptime(request.form.get('start_date', ''), '%Y-%m-%d').date(),
            end_date=datetime.strptime(request.form.get('end_date', ''), '%Y-%m-%d').date(),
            progress=int(request.form.get('progress', 0)),
            status=request.form.get('status', 'Pendente'),
            order=int(request.form.get('order', 0) or 0),
            responsible_id=int(responsible_id) if responsible_id else None
        )
        db.session.add(milestone)
        db.session.commit()
        flash('Marco adicionado com sucesso!', 'success')
        return redirect(url_for('schedule.view_schedule', project_id=project_id))

    users = User.query.filter_by(tenant_id=tenant_id, active=True).order_by(User.full_name).all()
    return render_template('schedule/form.html', project=project, milestone=None, users=users)


@schedule_bp.route('/projects/<int:project_id>/schedule/<int:milestone_id>/edit', methods=['GET', 'POST'])
@login_required
@tenant_required
def edit_milestone(project_id, milestone_id):
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    milestone = Milestone.query.get_or_404(milestone_id)
    ensure_tenant_access(milestone)

    tenant_id = get_current_tenant_id()

    if request.method == 'POST':
        responsible_id = request.form.get('responsible_id')
        milestone.title = request.form.get('title', '').strip()
        milestone.description = request.form.get('description', '').strip()
        milestone.start_date = datetime.strptime(request.form.get('start_date', ''), '%Y-%m-%d').date()
        milestone.end_date = datetime.strptime(request.form.get('end_date', ''), '%Y-%m-%d').date()
        milestone.progress = int(request.form.get('progress', 0))
        milestone.status = request.form.get('status', 'Pendente')
        milestone.order = int(request.form.get('order', 0) or 0)
        milestone.responsible_id = int(responsible_id) if responsible_id else None

        db.session.commit()
        flash('Marco atualizado com sucesso!', 'success')
        return redirect(url_for('schedule.view_schedule', project_id=project_id))

    users = User.query.filter_by(tenant_id=tenant_id, active=True).order_by(User.full_name).all()
    return render_template('schedule/form.html', project=project, milestone=milestone, users=users)


@schedule_bp.route('/projects/<int:project_id>/schedule/<int:milestone_id>/delete', methods=['POST'])
@login_required
@tenant_required
def delete_milestone(project_id, milestone_id):
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    milestone = Milestone.query.get_or_404(milestone_id)
    ensure_tenant_access(milestone)

    db.session.delete(milestone)
    db.session.commit()
    flash('Marco excluído com sucesso!', 'success')
    return redirect(url_for('schedule.view_schedule', project_id=project_id))


@schedule_bp.route('/projects/<int:project_id>/schedule/<int:milestone_id>/progress', methods=['POST'])
@login_required
@tenant_required
def update_progress(project_id, milestone_id):
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    milestone = Milestone.query.get_or_404(milestone_id)
    ensure_tenant_access(milestone)

    progress = request.json.get('progress', 0)
    milestone.progress = max(0, min(100, int(progress)))
    if milestone.progress == 100:
        milestone.status = 'Concluído'
    elif milestone.progress > 0:
        milestone.status = 'Em Andamento'
    db.session.commit()
    return jsonify({'success': True, 'progress': milestone.progress, 'status': milestone.status})


@schedule_bp.route('/projects/<int:project_id>/schedule/export')
@login_required
@tenant_required
def export_schedule(project_id):
    """Export schedule to MS Project XML with resources."""
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    milestones = Milestone.query.filter_by(project_id=project_id).order_by(Milestone.order, Milestone.start_date).all()
    resources = Resource.query.filter_by(project_id=project_id, type='Pessoa', status='Ativo').all()

    # Create MS Project XML
    root = ET.Element('Project')
    root.set('xmlns', 'http://schemas.microsoft.com/project')

    ET.SubElement(root, 'Name').text = project.title
    ET.SubElement(root, 'Title').text = project.title
    if project.start_date:
        ET.SubElement(root, 'StartDate').text = project.start_date.isoformat()
    if project.end_date:
        ET.SubElement(root, 'FinishDate').text = project.end_date.isoformat()

    # Resources section
    resources_elem = ET.SubElement(root, 'Resources')
    resource_uid_map = {}
    for i, resource in enumerate(resources, 1):
        res_elem = ET.SubElement(resources_elem, 'Resource')
        ET.SubElement(res_elem, 'UID').text = str(i)
        ET.SubElement(res_elem, 'ID').text = str(i)
        ET.SubElement(res_elem, 'Name').text = resource.name
        ET.SubElement(res_elem, 'Type').text = '1'  # Work resource
        if resource.role:
            ET.SubElement(res_elem, 'Group').text = resource.role
        if resource.hourly_cost:
            ET.SubElement(res_elem, 'StandardRate').text = str(resource.hourly_cost)
        resource_uid_map[resource.id] = i

    # Also add users as resources (for responsible field)
    user_uid_map = {}
    user_offset = len(resources)
    users_with_milestones = set(m.responsible_id for m in milestones if m.responsible_id)
    for i, user_id in enumerate(users_with_milestones, user_offset + 1):
        user = User.query.get(user_id)
        if user:
            res_elem = ET.SubElement(resources_elem, 'Resource')
            ET.SubElement(res_elem, 'UID').text = str(i)
            ET.SubElement(res_elem, 'ID').text = str(i)
            ET.SubElement(res_elem, 'Name').text = user.full_name
            ET.SubElement(res_elem, 'Type').text = '1'
            user_uid_map[user_id] = i

    # Tasks section
    tasks = ET.SubElement(root, 'Tasks')
    for i, milestone in enumerate(milestones, 1):
        task = ET.SubElement(tasks, 'Task')
        ET.SubElement(task, 'UID').text = str(i)
        ET.SubElement(task, 'ID').text = str(i)
        ET.SubElement(task, 'Name').text = milestone.title
        if milestone.description:
            ET.SubElement(task, 'Notes').text = milestone.description
        if milestone.start_date:
            ET.SubElement(task, 'Start').text = milestone.start_date.isoformat() + 'T08:00:00'
        if milestone.end_date:
            ET.SubElement(task, 'Finish').text = milestone.end_date.isoformat() + 'T17:00:00'
        ET.SubElement(task, 'PercentComplete').text = str(milestone.progress or 0)
        ET.SubElement(task, 'Priority').text = '500'

    # Assignments section (links tasks to resources)
    assignments = ET.SubElement(root, 'Assignments')
    assign_uid = 1
    for i, milestone in enumerate(milestones, 1):
        if milestone.responsible_id and milestone.responsible_id in user_uid_map:
            assign = ET.SubElement(assignments, 'Assignment')
            ET.SubElement(assign, 'UID').text = str(assign_uid)
            ET.SubElement(assign, 'TaskUID').text = str(i)
            ET.SubElement(assign, 'ResourceUID').text = str(user_uid_map[milestone.responsible_id])
            assign_uid += 1

    xml_str = ET.tostring(root, encoding='unicode', method='xml')
    xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str

    return Response(
        xml_content,
        mimetype='application/xml',
        headers={'Content-Disposition': f'attachment; filename=cronograma_{project.code}.xml'}
    )


@schedule_bp.route('/projects/<int:project_id>/schedule/import', methods=['GET', 'POST'])
@login_required
@tenant_required
def import_schedule(project_id):
    """Import schedule from MS Project XML with resource assignments."""
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)
    tenant_id = get_current_tenant_id()

    if request.method == 'POST':
        if 'file' not in request.files:
            flash('Nenhum arquivo selecionado.', 'danger')
            return redirect(request.url)

        file = request.files['file']
        if file.filename == '':
            flash('Nenhum arquivo selecionado.', 'danger')
            return redirect(request.url)

        if not file.filename.endswith('.xml'):
            flash('Formato invalido. Use arquivo XML do MS Project.', 'danger')
            return redirect(request.url)

        try:
            content = file.read()
            root = ET.fromstring(content)

            # Handle namespace
            ns = {'ms': 'http://schemas.microsoft.com/project'}

            def find_all(parent, tag):
                return parent.findall(f'.//ms:{tag}', ns) or parent.findall(f'.//{tag}')

            def get_text(elem, tag):
                el = elem.find(f'ms:{tag}', ns) or elem.find(tag)
                return el.text if el is not None else None

            # Build resource map (UID -> name)
            resource_uid_to_name = {}
            for res in find_all(root, 'Resource'):
                uid = get_text(res, 'UID')
                name = get_text(res, 'Name')
                if uid and name:
                    resource_uid_to_name[uid] = name.strip()

            # Build assignment map (TaskUID -> ResourceUID)
            task_to_resource = {}
            for assign in find_all(root, 'Assignment'):
                task_uid = get_text(assign, 'TaskUID')
                res_uid = get_text(assign, 'ResourceUID')
                if task_uid and res_uid:
                    task_to_resource[task_uid] = res_uid

            # Map resource names to user IDs
            users = User.query.filter_by(tenant_id=tenant_id, active=True).all()
            user_name_to_id = {u.full_name.lower(): u.id for u in users}

            tasks = find_all(root, 'Task')
            imported = 0
            existing_count = Milestone.query.filter_by(project_id=project_id).count()

            for task in tasks:
                task_uid = get_text(task, 'UID')
                name = get_text(task, 'Name')
                if not name or name.strip() == '':
                    continue

                start = get_text(task, 'Start')
                finish = get_text(task, 'Finish')
                percent = get_text(task, 'PercentComplete')
                notes = get_text(task, 'Notes')

                # Parse dates
                start_date = None
                end_date = None
                if start:
                    try:
                        start_date = datetime.fromisoformat(start.replace('Z', '+00:00').split('T')[0]).date()
                    except:
                        pass
                if finish:
                    try:
                        end_date = datetime.fromisoformat(finish.replace('Z', '+00:00').split('T')[0]).date()
                    except:
                        pass

                progress = int(percent) if percent and percent.isdigit() else 0

                # Determine status
                if progress >= 100:
                    status = 'Concluido'
                elif progress > 0:
                    status = 'Em Andamento'
                else:
                    status = 'Pendente'

                # Find responsible from assignment
                responsible_id = None
                if task_uid and task_uid in task_to_resource:
                    res_uid = task_to_resource[task_uid]
                    res_name = resource_uid_to_name.get(res_uid, '').lower()
                    if res_name and res_name in user_name_to_id:
                        responsible_id = user_name_to_id[res_name]

                milestone = Milestone(
                    tenant_id=tenant_id,
                    project_id=project_id,
                    title=name.strip(),
                    description=notes.strip() if notes else '',
                    start_date=start_date,
                    end_date=end_date,
                    progress=progress,
                    status=status,
                    order=existing_count + imported,
                    responsible_id=responsible_id
                )
                db.session.add(milestone)
                imported += 1

            db.session.commit()
            flash(f'{imported} marcos importados com sucesso!', 'success')
            return redirect(url_for('schedule.view_schedule', project_id=project_id))

        except ET.ParseError as e:
            flash(f'Erro ao processar XML: {str(e)}', 'danger')
            return redirect(request.url)
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao importar: {str(e)}', 'danger')
            return redirect(request.url)

    return render_template('schedule/import.html', project=project)
