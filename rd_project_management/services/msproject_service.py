"""
MS Project XML Import/Export Service.
Handles import and export of project schedules to/from MS Project XML format.
"""
from datetime import datetime, date, timedelta
from xml.etree import ElementTree as ET
from xml.dom import minidom
import re

from models import db, Project, Milestone, Resource


def export_project_to_xml(project):
    """Export a single project to MS Project XML format."""
    root = ET.Element('Project')
    root.set('xmlns', 'http://schemas.microsoft.com/project')

    # Project metadata
    ET.SubElement(root, 'Name').text = f"{project.code} - {project.title}"
    ET.SubElement(root, 'Title').text = project.title
    ET.SubElement(root, 'Company').text = project.tenant.name if project.tenant else ''
    ET.SubElement(root, 'StartDate').text = project.start_date.isoformat() if project.start_date else date.today().isoformat()
    ET.SubElement(root, 'FinishDate').text = project.end_date.isoformat() if project.end_date else ''
    ET.SubElement(root, 'CreationDate').text = datetime.now().isoformat()

    # Calendar (standard)
    calendars = ET.SubElement(root, 'Calendars')
    calendar = ET.SubElement(calendars, 'Calendar')
    ET.SubElement(calendar, 'UID').text = '1'
    ET.SubElement(calendar, 'Name').text = 'Standard'
    ET.SubElement(calendar, 'IsBaseCalendar').text = '1'

    # Tasks (milestones)
    tasks = ET.SubElement(root, 'Tasks')

    # Add project summary task
    summary_task = ET.SubElement(tasks, 'Task')
    ET.SubElement(summary_task, 'UID').text = '0'
    ET.SubElement(summary_task, 'ID').text = '0'
    ET.SubElement(summary_task, 'Name').text = project.title
    ET.SubElement(summary_task, 'Type').text = '1'
    ET.SubElement(summary_task, 'IsNull').text = '0'
    ET.SubElement(summary_task, 'OutlineLevel').text = '0'

    milestones = Milestone.query.filter_by(project_id=project.id).order_by(Milestone.order, Milestone.start_date).all()

    for idx, milestone in enumerate(milestones, start=1):
        task = ET.SubElement(tasks, 'Task')
        ET.SubElement(task, 'UID').text = str(idx)
        ET.SubElement(task, 'ID').text = str(idx)
        ET.SubElement(task, 'Name').text = milestone.title
        ET.SubElement(task, 'Type').text = '0'  # Fixed Units
        ET.SubElement(task, 'IsNull').text = '0'
        ET.SubElement(task, 'OutlineLevel').text = '1'
        ET.SubElement(task, 'OutlineNumber').text = str(idx)
        ET.SubElement(task, 'Start').text = milestone.start_date.isoformat() + 'T08:00:00'
        ET.SubElement(task, 'Finish').text = milestone.end_date.isoformat() + 'T17:00:00'
        ET.SubElement(task, 'PercentComplete').text = str(milestone.progress or 0)
        ET.SubElement(task, 'Notes').text = milestone.description or ''

        # Duration in days
        if milestone.start_date and milestone.end_date:
            duration_days = (milestone.end_date - milestone.start_date).days + 1
            ET.SubElement(task, 'Duration').text = f'PT{duration_days * 8}H0M0S'

    # Resources
    resources_elem = ET.SubElement(root, 'Resources')
    project_resources = Resource.query.filter_by(project_id=project.id, type='Pessoa').all()

    for idx, resource in enumerate(project_resources, start=1):
        res = ET.SubElement(resources_elem, 'Resource')
        ET.SubElement(res, 'UID').text = str(idx)
        ET.SubElement(res, 'ID').text = str(idx)
        ET.SubElement(res, 'Name').text = resource.name
        ET.SubElement(res, 'Type').text = '1'  # Work
        ET.SubElement(res, 'MaxUnits').text = '1.0'
        if resource.hourly_cost:
            ET.SubElement(res, 'StandardRate').text = str(resource.hourly_cost)

    # Pretty print
    xml_str = ET.tostring(root, encoding='unicode')
    dom = minidom.parseString(xml_str)
    return dom.toprettyxml(indent='  ')


def export_program_to_xml(program):
    """Export a program with all its projects to MS Project XML."""
    root = ET.Element('Project')
    root.set('xmlns', 'http://schemas.microsoft.com/project')

    # Program metadata
    ET.SubElement(root, 'Name').text = f"Programa: {program.code} - {program.name}"
    ET.SubElement(root, 'Title').text = program.name
    ET.SubElement(root, 'Company').text = program.tenant.name if program.tenant else ''
    ET.SubElement(root, 'StartDate').text = program.start_date.isoformat() if program.start_date else date.today().isoformat()
    ET.SubElement(root, 'CreationDate').text = datetime.now().isoformat()

    # Calendar
    calendars = ET.SubElement(root, 'Calendars')
    calendar = ET.SubElement(calendars, 'Calendar')
    ET.SubElement(calendar, 'UID').text = '1'
    ET.SubElement(calendar, 'Name').text = 'Standard'
    ET.SubElement(calendar, 'IsBaseCalendar').text = '1'

    # Tasks
    tasks = ET.SubElement(root, 'Tasks')

    # Program summary task
    summary_task = ET.SubElement(tasks, 'Task')
    ET.SubElement(summary_task, 'UID').text = '0'
    ET.SubElement(summary_task, 'ID').text = '0'
    ET.SubElement(summary_task, 'Name').text = program.name
    ET.SubElement(summary_task, 'Type').text = '1'
    ET.SubElement(summary_task, 'OutlineLevel').text = '0'

    task_id = 1
    projects = Project.query.filter_by(program_id=program.id).all()

    for project in projects:
        # Project as summary task
        proj_task = ET.SubElement(tasks, 'Task')
        ET.SubElement(proj_task, 'UID').text = str(task_id)
        ET.SubElement(proj_task, 'ID').text = str(task_id)
        ET.SubElement(proj_task, 'Name').text = f"{project.code} - {project.title}"
        ET.SubElement(proj_task, 'Type').text = '1'
        ET.SubElement(proj_task, 'OutlineLevel').text = '1'
        ET.SubElement(proj_task, 'Start').text = project.start_date.isoformat() + 'T08:00:00' if project.start_date else ''
        ET.SubElement(proj_task, 'Finish').text = project.end_date.isoformat() + 'T17:00:00' if project.end_date else ''
        task_id += 1

        # Project milestones
        milestones = Milestone.query.filter_by(project_id=project.id).order_by(Milestone.order, Milestone.start_date).all()
        for milestone in milestones:
            task = ET.SubElement(tasks, 'Task')
            ET.SubElement(task, 'UID').text = str(task_id)
            ET.SubElement(task, 'ID').text = str(task_id)
            ET.SubElement(task, 'Name').text = milestone.title
            ET.SubElement(task, 'Type').text = '0'
            ET.SubElement(task, 'OutlineLevel').text = '2'
            ET.SubElement(task, 'Start').text = milestone.start_date.isoformat() + 'T08:00:00'
            ET.SubElement(task, 'Finish').text = milestone.end_date.isoformat() + 'T17:00:00'
            ET.SubElement(task, 'PercentComplete').text = str(milestone.progress or 0)

            if milestone.start_date and milestone.end_date:
                duration_days = (milestone.end_date - milestone.start_date).days + 1
                ET.SubElement(task, 'Duration').text = f'PT{duration_days * 8}H0M0S'
            task_id += 1

    # Pretty print
    xml_str = ET.tostring(root, encoding='unicode')
    dom = minidom.parseString(xml_str)
    return dom.toprettyxml(indent='  ')


def export_portfolio_to_xml(tenant_id):
    """Export entire portfolio to MS Project XML."""
    from models import Tenant

    tenant = Tenant.query.get(tenant_id)

    root = ET.Element('Project')
    root.set('xmlns', 'http://schemas.microsoft.com/project')

    ET.SubElement(root, 'Name').text = f"Portfolio: {tenant.name if tenant else 'Empresa'}"
    ET.SubElement(root, 'Title').text = f"Portfolio Completo"
    ET.SubElement(root, 'Company').text = tenant.name if tenant else ''
    ET.SubElement(root, 'CreationDate').text = datetime.now().isoformat()

    # Calendar
    calendars = ET.SubElement(root, 'Calendars')
    calendar = ET.SubElement(calendars, 'Calendar')
    ET.SubElement(calendar, 'UID').text = '1'
    ET.SubElement(calendar, 'Name').text = 'Standard'
    ET.SubElement(calendar, 'IsBaseCalendar').text = '1'

    tasks = ET.SubElement(root, 'Tasks')

    # Portfolio summary
    summary_task = ET.SubElement(tasks, 'Task')
    ET.SubElement(summary_task, 'UID').text = '0'
    ET.SubElement(summary_task, 'ID').text = '0'
    ET.SubElement(summary_task, 'Name').text = f"Portfolio {tenant.name if tenant else ''}"
    ET.SubElement(summary_task, 'Type').text = '1'
    ET.SubElement(summary_task, 'OutlineLevel').text = '0'

    task_id = 1
    projects = Project.query.filter_by(tenant_id=tenant_id).order_by(Project.code).all()

    for project in projects:
        # Project as summary task
        proj_task = ET.SubElement(tasks, 'Task')
        ET.SubElement(proj_task, 'UID').text = str(task_id)
        ET.SubElement(proj_task, 'ID').text = str(task_id)
        ET.SubElement(proj_task, 'Name').text = f"{project.code} - {project.title}"
        ET.SubElement(proj_task, 'Type').text = '1'
        ET.SubElement(proj_task, 'OutlineLevel').text = '1'
        if project.start_date:
            ET.SubElement(proj_task, 'Start').text = project.start_date.isoformat() + 'T08:00:00'
        if project.end_date:
            ET.SubElement(proj_task, 'Finish').text = project.end_date.isoformat() + 'T17:00:00'
        task_id += 1

        # Milestones
        milestones = Milestone.query.filter_by(project_id=project.id).order_by(Milestone.order, Milestone.start_date).all()
        for milestone in milestones:
            task = ET.SubElement(tasks, 'Task')
            ET.SubElement(task, 'UID').text = str(task_id)
            ET.SubElement(task, 'ID').text = str(task_id)
            ET.SubElement(task, 'Name').text = milestone.title
            ET.SubElement(task, 'Type').text = '0'
            ET.SubElement(task, 'OutlineLevel').text = '2'
            ET.SubElement(task, 'Start').text = milestone.start_date.isoformat() + 'T08:00:00'
            ET.SubElement(task, 'Finish').text = milestone.end_date.isoformat() + 'T17:00:00'
            ET.SubElement(task, 'PercentComplete').text = str(milestone.progress or 0)

            if milestone.start_date and milestone.end_date:
                duration_days = (milestone.end_date - milestone.start_date).days + 1
                ET.SubElement(task, 'Duration').text = f'PT{duration_days * 8}H0M0S'
            task_id += 1

    xml_str = ET.tostring(root, encoding='unicode')
    dom = minidom.parseString(xml_str)
    return dom.toprettyxml(indent='  ')


def import_project_from_xml(xml_content, project):
    """Import milestones from MS Project XML into a project."""
    root = ET.fromstring(xml_content)

    # Find namespace if present
    ns = ''
    if root.tag.startswith('{'):
        ns = root.tag.split('}')[0] + '}'

    tasks_elem = root.find(f'{ns}Tasks')
    if tasks_elem is None:
        return 0, "Nenhuma tarefa encontrada no arquivo"

    imported_count = 0

    for task in tasks_elem.findall(f'{ns}Task'):
        # Skip summary tasks (outline level 0)
        outline_level = task.find(f'{ns}OutlineLevel')
        if outline_level is not None and outline_level.text == '0':
            continue

        name_elem = task.find(f'{ns}Name')
        if name_elem is None or not name_elem.text:
            continue

        # Parse dates
        start_elem = task.find(f'{ns}Start')
        finish_elem = task.find(f'{ns}Finish')
        percent_elem = task.find(f'{ns}PercentComplete')
        notes_elem = task.find(f'{ns}Notes')

        start_date = None
        end_date = None

        if start_elem is not None and start_elem.text:
            try:
                start_date = datetime.fromisoformat(start_elem.text.split('T')[0]).date()
            except:
                pass

        if finish_elem is not None and finish_elem.text:
            try:
                end_date = datetime.fromisoformat(finish_elem.text.split('T')[0]).date()
            except:
                pass

        if not start_date:
            start_date = date.today()
        if not end_date:
            end_date = start_date + timedelta(days=7)

        progress = 0
        if percent_elem is not None and percent_elem.text:
            try:
                progress = int(float(percent_elem.text))
            except:
                pass

        # Create milestone
        milestone = Milestone(
            tenant_id=project.tenant_id,
            project_id=project.id,
            title=name_elem.text[:300],
            description=notes_elem.text if notes_elem is not None else None,
            start_date=start_date,
            end_date=end_date,
            progress=progress,
            status='Concluido' if progress >= 100 else 'Em Andamento' if progress > 0 else 'Pendente',
            order=imported_count
        )
        db.session.add(milestone)
        imported_count += 1

    if imported_count > 0:
        db.session.commit()

    return imported_count, f"{imported_count} marcos importados com sucesso"
