from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, send_file, Response
from flask_login import login_required
from models import db, Milestone, MilestoneResource, Project, User, Resource
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
        predecessor_id = request.form.get('predecessor_id')
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
            predecessor_id=int(predecessor_id) if predecessor_id else None
        )
        # Validate allocation total
        resource_ids = request.form.getlist('resource_ids')
        allocations = request.form.getlist('allocations')
        total_allocation = 0
        for i, res_id in enumerate(resource_ids):
            if res_id:
                alloc = int(allocations[i]) if i < len(allocations) and allocations[i] else 100
                total_allocation += alloc

        if total_allocation > 100:
            flash('A soma das alocações não pode ultrapassar 100%!', 'danger')
            resources = Resource.query.filter_by(project_id=project_id, type='Pessoa', status='Ativo').order_by(Resource.name).all()
            all_milestones = Milestone.query.filter_by(project_id=project_id).order_by(Milestone.order, Milestone.start_date).all()
            return render_template('schedule/form.html', project=project, milestone=None, resources=resources, all_milestones=all_milestones)

        db.session.add(milestone)
        db.session.flush()  # Get milestone.id

        # Add responsible resources with allocation
        for i, res_id in enumerate(resource_ids):
            if res_id:
                alloc = int(allocations[i]) if i < len(allocations) and allocations[i] else 100
                mr = MilestoneResource(
                    milestone_id=milestone.id,
                    resource_id=int(res_id),
                    allocation=alloc
                )
                db.session.add(mr)

        db.session.commit()
        flash('Marco adicionado com sucesso!', 'success')
        return redirect(url_for('schedule.view_schedule', project_id=project_id))

    resources = Resource.query.filter_by(project_id=project_id, type='Pessoa', status='Ativo').order_by(Resource.name).all()
    all_milestones = Milestone.query.filter_by(project_id=project_id).order_by(Milestone.order, Milestone.start_date).all()
    return render_template('schedule/form.html', project=project, milestone=None, resources=resources, all_milestones=all_milestones)


@schedule_bp.route('/projects/<int:project_id>/schedule/<int:milestone_id>/edit', methods=['GET', 'POST'])
@login_required
@tenant_required
def edit_milestone(project_id, milestone_id):
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    milestone = Milestone.query.get_or_404(milestone_id)
    ensure_tenant_access(milestone)

    if request.method == 'POST':
        predecessor_id = request.form.get('predecessor_id')
        milestone.title = request.form.get('title', '').strip()
        milestone.description = request.form.get('description', '').strip()
        milestone.start_date = datetime.strptime(request.form.get('start_date', ''), '%Y-%m-%d').date()
        milestone.end_date = datetime.strptime(request.form.get('end_date', ''), '%Y-%m-%d').date()
        milestone.progress = int(request.form.get('progress', 0))
        milestone.status = request.form.get('status', 'Pendente')
        milestone.order = int(request.form.get('order', 0) or 0)
        milestone.predecessor_id = int(predecessor_id) if predecessor_id else None

        # Validate allocation total
        resource_ids = request.form.getlist('resource_ids')
        allocations = request.form.getlist('allocations')
        total_allocation = 0
        for i, res_id in enumerate(resource_ids):
            if res_id:
                alloc = int(allocations[i]) if i < len(allocations) and allocations[i] else 100
                total_allocation += alloc

        if total_allocation > 100:
            flash('A soma das alocações não pode ultrapassar 100%!', 'danger')
            resources = Resource.query.filter_by(project_id=project_id, type='Pessoa', status='Ativo').order_by(Resource.name).all()
            all_milestones = Milestone.query.filter_by(project_id=project_id).order_by(Milestone.order, Milestone.start_date).all()
            return render_template('schedule/form.html', project=project, milestone=milestone, resources=resources, all_milestones=all_milestones)

        # Update responsible resources
        MilestoneResource.query.filter_by(milestone_id=milestone.id).delete()
        for i, res_id in enumerate(resource_ids):
            if res_id:
                alloc = int(allocations[i]) if i < len(allocations) and allocations[i] else 100
                mr = MilestoneResource(
                    milestone_id=milestone.id,
                    resource_id=int(res_id),
                    allocation=alloc
                )
                db.session.add(mr)

        db.session.commit()
        flash('Marco atualizado com sucesso!', 'success')
        return redirect(url_for('schedule.view_schedule', project_id=project_id))

    resources = Resource.query.filter_by(project_id=project_id, type='Pessoa', status='Ativo').order_by(Resource.name).all()
    all_milestones = Milestone.query.filter_by(project_id=project_id).order_by(Milestone.order, Milestone.start_date).all()
    return render_template('schedule/form.html', project=project, milestone=milestone, resources=resources, all_milestones=all_milestones)


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

    # Resources section (pessoas do projeto)
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

    # Tasks section
    tasks = ET.SubElement(root, 'Tasks')
    milestone_uid_map = {}
    for i, milestone in enumerate(milestones, 1):
        milestone_uid_map[milestone.id] = i
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

        # Add predecessor link (Finish-to-Start)
        if milestone.predecessor_id and milestone.predecessor_id in milestone_uid_map:
            pred_link = ET.SubElement(task, 'PredecessorLink')
            ET.SubElement(pred_link, 'PredecessorUID').text = str(milestone_uid_map[milestone.predecessor_id])
            ET.SubElement(pred_link, 'Type').text = '1'  # 1 = Finish-to-Start (FS)
            ET.SubElement(pred_link, 'LinkLag').text = '0'

    # Assignments section (links tasks to resources - supports multiple per task)
    assignments = ET.SubElement(root, 'Assignments')
    assign_uid = 1
    for i, milestone in enumerate(milestones, 1):
        for ra in milestone.resource_assignments:
            if ra.resource_id in resource_uid_map:
                assign = ET.SubElement(assignments, 'Assignment')
                ET.SubElement(assign, 'UID').text = str(assign_uid)
                ET.SubElement(assign, 'TaskUID').text = str(i)
                ET.SubElement(assign, 'ResourceUID').text = str(resource_uid_map[ra.resource_id])
                ET.SubElement(assign, 'Units').text = str(ra.allocation / 100)  # MS Project uses decimal (1.0 = 100%)
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

            # Build assignment map (TaskUID -> list of (ResourceUID, allocation))
            task_to_resources = {}
            for assign in find_all(root, 'Assignment'):
                task_uid = get_text(assign, 'TaskUID')
                res_uid = get_text(assign, 'ResourceUID')
                units = get_text(assign, 'Units')
                if task_uid and res_uid:
                    allocation = int(float(units or 1) * 100)  # Convert from decimal to percentage
                    if task_uid not in task_to_resources:
                        task_to_resources[task_uid] = []
                    task_to_resources[task_uid].append((res_uid, allocation))

            # Build predecessor map (TaskUID -> PredecessorUID)
            task_to_predecessor = {}
            tasks_temp = find_all(root, 'Task')
            for task in tasks_temp:
                task_uid = get_text(task, 'UID')
                pred_link = task.find('ms:PredecessorLink', ns) or task.find('PredecessorLink')
                if pred_link is not None:
                    pred_uid = get_text(pred_link, 'PredecessorUID')
                    if pred_uid:
                        task_to_predecessor[task_uid] = pred_uid

            # Map resource names to project resource IDs
            project_resources = Resource.query.filter_by(project_id=project_id, type='Pessoa').all()
            resource_name_to_id = {r.name.lower(): r.id for r in project_resources}

            tasks = find_all(root, 'Task')
            imported = 0
            existing_count = Milestone.query.filter_by(project_id=project_id).count()
            task_uid_to_milestone_id = {}  # Map TaskUID to new milestone ID

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

                milestone = Milestone(
                    tenant_id=tenant_id,
                    project_id=project_id,
                    title=name.strip(),
                    description=notes.strip() if notes else '',
                    start_date=start_date,
                    end_date=end_date,
                    progress=progress,
                    status=status,
                    order=existing_count + imported
                )
                db.session.add(milestone)
                db.session.flush()  # Get milestone.id

                # Track TaskUID to milestone ID mapping
                if task_uid:
                    task_uid_to_milestone_id[task_uid] = milestone.id

                # Add responsible resources from assignments
                if task_uid and task_uid in task_to_resources:
                    for res_uid, allocation in task_to_resources[task_uid]:
                        res_name = resource_uid_to_name.get(res_uid, '').lower()
                        if res_name and res_name in resource_name_to_id:
                            mr = MilestoneResource(
                                milestone_id=milestone.id,
                                resource_id=resource_name_to_id[res_name],
                                allocation=allocation
                            )
                            db.session.add(mr)

                imported += 1

            # Update predecessor relationships
            for task_uid, pred_uid in task_to_predecessor.items():
                if task_uid in task_uid_to_milestone_id and pred_uid in task_uid_to_milestone_id:
                    milestone = Milestone.query.get(task_uid_to_milestone_id[task_uid])
                    if milestone:
                        milestone.predecessor_id = task_uid_to_milestone_id[pred_uid]

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
