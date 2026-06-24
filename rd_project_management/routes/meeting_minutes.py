"""
Meeting Minutes routes for project meetings.
Allows creating, editing, and generating AI-powered meeting minutes.
"""
import os
import uuid
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from flask_login import login_required, current_user
from flask_babel import _
from werkzeug.utils import secure_filename
from datetime import datetime, date

from models import db, MeetingMinutes, Project, AuditLog
from services.tenant_utils import tenant_required, ensure_tenant_access, get_current_tenant_id
from services.ai_service import get_anthropic_client, extract_text_from_pdf

meeting_minutes_bp = Blueprint('meeting_minutes', __name__)


def allowed_file(filename):
    """Check if file extension is allowed."""
    allowed = {'pdf', 'doc', 'docx', 'txt'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed


@meeting_minutes_bp.route('/projects/<int:project_id>/atas')
@login_required
@tenant_required
def list_minutes(project_id):
    """List all meeting minutes for a project."""
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    minutes = MeetingMinutes.query.filter_by(project_id=project_id)\
        .order_by(MeetingMinutes.meeting_date.desc()).all()

    return render_template('meeting_minutes/list.html', project=project, minutes=minutes)


@meeting_minutes_bp.route('/projects/<int:project_id>/atas/nova', methods=['GET', 'POST'])
@login_required
@tenant_required
def create_minutes(project_id):
    """Create new meeting minutes."""
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    tenant_id = get_current_tenant_id()

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        meeting_date_str = request.form.get('meeting_date', '')
        meeting_time = request.form.get('meeting_time', '').strip()
        location = request.form.get('location', '').strip()
        participants = request.form.get('participants', '').strip()
        transcription = request.form.get('transcription', '').strip()

        if not title:
            flash(_('Título é obrigatório.'), 'danger')
            return render_template('meeting_minutes/form.html', project=project, minutes=None)

        try:
            meeting_date = datetime.strptime(meeting_date_str, '%Y-%m-%d').date()
        except ValueError:
            meeting_date = date.today()

        minutes = MeetingMinutes(
            tenant_id=tenant_id,
            project_id=project_id,
            title=title,
            meeting_date=meeting_date,
            meeting_time=meeting_time,
            location=location,
            participants=participants,
            transcription=transcription,
            created_by_id=current_user.id,
            status='Rascunho'
        )

        # Handle file upload
        if 'attachment' in request.files:
            file = request.files['attachment']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                stored_filename = f"{uuid.uuid4()}_{filename}"

                tenant_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], str(tenant_id))
                os.makedirs(tenant_folder, exist_ok=True)

                file_path = os.path.join(tenant_folder, stored_filename)
                file.save(file_path)

                minutes.attachment_filename = filename
                minutes.attachment_stored = stored_filename

                # Extract text from PDF if applicable
                if filename.lower().endswith('.pdf'):
                    try:
                        extracted = extract_text_from_pdf(file_path)
                        if extracted and not transcription:
                            minutes.transcription = extracted
                    except Exception:
                        pass

        db.session.add(minutes)
        db.session.commit()

        try:
            AuditLog.log(action='create', entity_type='meeting_minutes', entity_id=minutes.id, entity_name=title)
            db.session.commit()
        except Exception:
            pass

        flash(_('Ata criada com sucesso!'), 'success')
        return redirect(url_for('meeting_minutes.view_minutes', project_id=project_id, minutes_id=minutes.id))

    return render_template('meeting_minutes/form.html', project=project, minutes=None)


@meeting_minutes_bp.route('/projects/<int:project_id>/atas/<int:minutes_id>')
@login_required
@tenant_required
def view_minutes(project_id, minutes_id):
    """View meeting minutes."""
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    minutes = MeetingMinutes.query.get_or_404(minutes_id)
    ensure_tenant_access(minutes)

    tenant = current_user.tenant

    return render_template('meeting_minutes/view.html', project=project, minutes=minutes, tenant=tenant)


@meeting_minutes_bp.route('/projects/<int:project_id>/atas/<int:minutes_id>/editar', methods=['GET', 'POST'])
@login_required
@tenant_required
def edit_minutes(project_id, minutes_id):
    """Edit meeting minutes."""
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    minutes = MeetingMinutes.query.get_or_404(minutes_id)
    ensure_tenant_access(minutes)

    if request.method == 'POST':
        minutes.title = request.form.get('title', '').strip()
        meeting_date_str = request.form.get('meeting_date', '')
        minutes.meeting_time = request.form.get('meeting_time', '').strip()
        minutes.location = request.form.get('location', '').strip()
        minutes.participants = request.form.get('participants', '').strip()
        minutes.transcription = request.form.get('transcription', '').strip()

        try:
            minutes.meeting_date = datetime.strptime(meeting_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass

        # Handle new file upload
        if 'attachment' in request.files:
            file = request.files['attachment']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                stored_filename = f"{uuid.uuid4()}_{filename}"

                tenant_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], str(minutes.tenant_id))
                os.makedirs(tenant_folder, exist_ok=True)

                file_path = os.path.join(tenant_folder, stored_filename)
                file.save(file_path)

                # Remove old file
                if minutes.attachment_stored:
                    old_path = os.path.join(tenant_folder, minutes.attachment_stored)
                    if os.path.exists(old_path):
                        os.remove(old_path)

                minutes.attachment_filename = filename
                minutes.attachment_stored = stored_filename

        db.session.commit()

        try:
            AuditLog.log(action='update', entity_type='meeting_minutes', entity_id=minutes.id, entity_name=minutes.title)
            db.session.commit()
        except Exception:
            pass

        flash(_('Ata atualizada com sucesso!'), 'success')
        return redirect(url_for('meeting_minutes.view_minutes', project_id=project_id, minutes_id=minutes_id))

    return render_template('meeting_minutes/form.html', project=project, minutes=minutes)


@meeting_minutes_bp.route('/projects/<int:project_id>/atas/<int:minutes_id>/excluir', methods=['POST'])
@login_required
@tenant_required
def delete_minutes(project_id, minutes_id):
    """Delete meeting minutes."""
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    minutes = MeetingMinutes.query.get_or_404(minutes_id)
    ensure_tenant_access(minutes)

    # Remove attachment file
    if minutes.attachment_stored:
        tenant_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], str(minutes.tenant_id))
        file_path = os.path.join(tenant_folder, minutes.attachment_stored)
        if os.path.exists(file_path):
            os.remove(file_path)

    try:
        AuditLog.log(action='delete', entity_type='meeting_minutes', entity_id=minutes.id, entity_name=minutes.title)
    except Exception:
        pass

    db.session.delete(minutes)
    db.session.commit()

    flash(_('Ata excluída com sucesso!'), 'success')
    return redirect(url_for('meeting_minutes.list_minutes', project_id=project_id))


@meeting_minutes_bp.route('/projects/<int:project_id>/atas/<int:minutes_id>/gerar', methods=['POST'])
@login_required
@tenant_required
def generate_minutes(project_id, minutes_id):
    """Generate meeting minutes using AI."""
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    minutes = MeetingMinutes.query.get_or_404(minutes_id)
    ensure_tenant_access(minutes)

    client = get_anthropic_client()
    if not client:
        return jsonify({'error': 'API de IA não configurada'}), 400

    if not minutes.transcription:
        return jsonify({'error': 'Nenhuma transcrição disponível para gerar a ata'}), 400

    tenant = current_user.tenant
    company_name = tenant.name if tenant else 'Empresa'

    prompt = f"""Você é um secretário executivo especializado em elaborar atas de reunião profissionais.

Com base na transcrição/anotações abaixo, gere uma ata de reunião formal e bem estruturada.

INFORMAÇÕES DA REUNIÃO:
- Empresa: {company_name}
- Projeto: {project.title} ({project.code})
- Título: {minutes.title}
- Data: {minutes.meeting_date.strftime('%d/%m/%Y')}
- Horário: {minutes.meeting_time or 'Não informado'}
- Local: {minutes.location or 'Não informado'}
- Participantes: {minutes.participants or 'Não informado'}

TRANSCRIÇÃO/ANOTAÇÕES:
{minutes.transcription}

Gere a ata no seguinte formato em Markdown:

# ATA DE REUNIÃO

**Projeto:** [código - título]
**Data:** [data]
**Horário:** [horário]
**Local:** [local]

## Participantes
[Lista de participantes]

## Pauta
[Tópicos discutidos]

## Discussões e Deliberações
[Resumo estruturado das discussões, organizadas por tópico]

## Decisões Tomadas
[Lista numerada das decisões]

## Ações e Responsáveis
| Ação | Responsável | Prazo |
|------|-------------|-------|
[Tabela com ações definidas]

## Pendências
[Lista de itens pendentes, se houver]

## Próximos Passos
[Próximas ações ou reunião]

---
*Ata gerada em {datetime.now().strftime('%d/%m/%Y às %H:%M')}*

Seja objetivo, profissional e capture todos os pontos importantes da discussão.
"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}]
        )

        generated = response.content[0].text
        minutes.generated_minutes = generated
        minutes.status = 'Gerada'
        db.session.commit()

        return jsonify({'success': True, 'minutes': generated})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@meeting_minutes_bp.route('/projects/<int:project_id>/atas/<int:minutes_id>/salvar-ata', methods=['POST'])
@login_required
@tenant_required
def save_generated(project_id, minutes_id):
    """Save edited generated minutes."""
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    minutes = MeetingMinutes.query.get_or_404(minutes_id)
    ensure_tenant_access(minutes)

    data = request.get_json()
    if data and 'minutes' in data:
        minutes.generated_minutes = data['minutes']
        minutes.status = 'Finalizada'
        db.session.commit()
        return jsonify({'success': True})

    return jsonify({'error': 'Dados inválidos'}), 400


@meeting_minutes_bp.route('/projects/<int:project_id>/atas/<int:minutes_id>/imprimir')
@login_required
@tenant_required
def print_minutes(project_id, minutes_id):
    """Print-friendly version of meeting minutes."""
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    minutes = MeetingMinutes.query.get_or_404(minutes_id)
    ensure_tenant_access(minutes)

    tenant = current_user.tenant

    return render_template('meeting_minutes/print.html', project=project, minutes=minutes, tenant=tenant)
