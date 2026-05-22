"""
AI Routes for R&D Project Management System.
Provides AI-powered features: document analysis, matching, reports, risks, chat.
"""
import os
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, current_app, session
from flask_login import login_required, current_user

from models import db, Project, PublicCall, ProjectDocument, Expense, Milestone, Resource, Timesheet
from services.tenant_utils import tenant_required, get_current_tenant_id, ensure_tenant_access
from services.ai_service import (
    analyze_public_call,
    match_project_to_calls,
    generate_project_report,
    analyze_project_risks,
    chat_assistant,
    get_system_context,
    extract_text_from_pdf
)

ai_bp = Blueprint('ai', __name__)


def check_ai_configured():
    """Check if AI is properly configured."""
    return bool(os.environ.get('ANTHROPIC_API_KEY'))


@ai_bp.route('/ai')
@login_required
@tenant_required
def ai_dashboard():
    """AI features dashboard."""
    # Get projects for the current tenant
    tenant_id = get_current_tenant_id()
    if current_user.is_superadmin():
        projects = Project.query.all()
    else:
        projects = Project.query.filter_by(tenant_id=tenant_id).all()

    return render_template('ai/dashboard.html', ai_configured=check_ai_configured(), projects=projects)


# --- Document Analysis ---

@ai_bp.route('/ai/analyze-document/<int:doc_id>')
@login_required
@tenant_required
def analyze_document_page(doc_id):
    """Page to analyze a document."""
    doc = ProjectDocument.query.get_or_404(doc_id)
    ensure_tenant_access(doc)

    return render_template('ai/analyze_document.html', document=doc, ai_configured=check_ai_configured())


@ai_bp.route('/ai/analyze-document/<int:doc_id>/run', methods=['POST'])
@login_required
@tenant_required
def run_document_analysis(doc_id):
    """Run AI analysis on a document."""
    if not check_ai_configured():
        return jsonify({'error': 'API de IA não configurada. Configure ANTHROPIC_API_KEY.'}), 400

    doc = ProjectDocument.query.get_or_404(doc_id)
    ensure_tenant_access(doc)

    # Only analyze PDFs for now
    if doc.file_type != 'pdf':
        return jsonify({'error': 'Apenas documentos PDF podem ser analisados.'}), 400

    # Get file path
    tenant_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], str(doc.tenant_id or 'global'))
    file_path = os.path.join(tenant_folder, doc.stored_filename)

    if not os.path.exists(file_path):
        return jsonify({'error': 'Arquivo não encontrado no servidor.'}), 404

    # Extract text from PDF
    text = extract_text_from_pdf(file_path)
    if not text:
        return jsonify({'error': 'Não foi possível extrair texto do PDF. Verifique se o PDF contém texto selecionável.'}), 400

    # Analyze with AI
    result = analyze_public_call(text)
    if result is None:
        return jsonify({'error': 'Erro ao conectar com a API de IA.'}), 500

    if 'error' in result:
        return jsonify({'error': result['error']}), 500

    return jsonify(result)


# --- Project-Call Matching ---

@ai_bp.route('/ai/matching/<int:project_id>')
@login_required
@tenant_required
def matching_page(project_id):
    """Page to match project with public calls."""
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    return render_template('ai/matching.html', project=project, ai_configured=check_ai_configured())


@ai_bp.route('/ai/matching/<int:project_id>/run', methods=['POST'])
@login_required
@tenant_required
def run_matching(project_id):
    """Run AI matching between project and public calls."""
    if not check_ai_configured():
        return jsonify({'error': 'API de IA não configurada. Configure ANTHROPIC_API_KEY.'}), 400

    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    # Get open public calls
    tenant_id = get_current_tenant_id()
    calls_query = PublicCall.query.filter(
        PublicCall.status == 'Aberta'
    ).filter(
        (PublicCall.tenant_id == tenant_id) | (PublicCall.tenant_id.is_(None))
    )
    calls = calls_query.all()

    if not calls:
        return jsonify({'error': 'Não há chamadas públicas abertas para comparar.'}), 400

    # Prepare project data
    project_data = {
        'title': project.title,
        'description': project.description,
        'category': project.category,
        'budget': project.budget,
        'start_date': str(project.start_date) if project.start_date else None,
        'end_date': str(project.end_date) if project.end_date else None,
        'funding_source': project.funding_source
    }

    # Prepare calls data
    calls_data = [{
        'id': c.id,
        'title': c.title,
        'source': c.source,
        'theme': c.theme,
        'description': c.description,
        'deadline': c.deadline,
        'target_audience': c.target_audience
    } for c in calls]

    # Run matching
    matches = match_project_to_calls(project_data, calls_data)

    # Enrich with call objects
    for match in matches:
        call = PublicCall.query.get(match.get('call_id'))
        if call:
            match['call_title'] = call.title
            match['call_source'] = call.source
            match['call_url'] = call.url
            match['call_deadline'] = call.deadline

    return jsonify({'matches': matches})


# --- Report Generation ---

@ai_bp.route('/ai/report/<int:project_id>')
@login_required
@tenant_required
def report_page(project_id):
    """Page to generate project reports."""
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    return render_template('ai/report.html', project=project, ai_configured=check_ai_configured())


@ai_bp.route('/ai/report/<int:project_id>/generate', methods=['POST'])
@login_required
@tenant_required
def generate_report(project_id):
    """Generate AI report for a project."""
    if not check_ai_configured():
        return jsonify({'error': 'API de IA não configurada. Configure ANTHROPIC_API_KEY.'}), 400

    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    report_type = request.json.get('type', 'parcial')

    # Gather project data
    project_data = {
        'code': project.code,
        'title': project.title,
        'description': project.description,
        'status': project.status,
        'category': project.category,
        'start_date': str(project.start_date) if project.start_date else None,
        'end_date': str(project.end_date) if project.end_date else None,
        'budget': project.budget,
        'funding_source': project.funding_source,
        'expenses': [{
            'description': e.description,
            'category': e.category,
            'amount': e.amount,
            'date': str(e.date)
        } for e in project.expenses],
        'milestones': [{
            'title': m.title,
            'description': m.description,
            'progress': m.progress,
            'status': m.status,
            'start_date': str(m.start_date),
            'end_date': str(m.end_date)
        } for m in project.milestones],
        'resources': [{
            'name': r.name,
            'type': r.type,
            'role': r.role,
            'hours_allocated': r.hours_allocated
        } for r in project.resources],
        'timesheets': [{
            'hours': t.hours,
            'activity': t.activity,
            'date': str(t.date)
        } for t in project.timesheets]
    }

    report = generate_project_report(project_data, report_type)

    if report is None:
        return jsonify({'error': 'Erro ao gerar relatório.'}), 500

    return jsonify({'report': report})


# --- Risk Analysis ---

@ai_bp.route('/ai/risks/<int:project_id>')
@login_required
@tenant_required
def risks_page(project_id):
    """Page to analyze project risks."""
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    return render_template('ai/risks.html', project=project, ai_configured=check_ai_configured())


@ai_bp.route('/ai/risks/<int:project_id>/analyze', methods=['POST'])
@login_required
@tenant_required
def analyze_risks(project_id):
    """Analyze project risks with AI."""
    if not check_ai_configured():
        return jsonify({'error': 'API de IA não configurada. Configure ANTHROPIC_API_KEY.'}), 400

    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    # Gather project data
    project_data = {
        'title': project.title,
        'status': project.status,
        'start_date': project.start_date,
        'end_date': project.end_date,
        'budget': project.budget,
        'expenses': [{
            'amount': e.amount,
            'date': e.date,
            'category': e.category
        } for e in project.expenses],
        'milestones': [{
            'title': m.title,
            'progress': m.progress,
            'status': m.status,
            'end_date': m.end_date
        } for m in project.milestones],
        'resources': [{
            'name': r.name,
            'hours_allocated': r.hours_allocated
        } for r in project.resources]
    }

    analysis = analyze_project_risks(project_data)

    if analysis is None:
        return jsonify({'error': 'Erro ao analisar riscos.'}), 500

    if 'error' in analysis:
        return jsonify({'error': analysis['error']}), 500

    return jsonify(analysis)


# --- Chat Assistant ---

@ai_bp.route('/ai/chat')
@login_required
@tenant_required
def chat_page():
    """AI Chat assistant page."""
    return render_template('ai/chat.html', ai_configured=check_ai_configured())


@ai_bp.route('/ai/chat/message', methods=['POST'])
@login_required
@tenant_required
def chat_message():
    """Send message to AI chat assistant."""
    if not check_ai_configured():
        return jsonify({'error': 'API de IA não configurada. Configure ANTHROPIC_API_KEY.'}), 400

    message = request.json.get('message', '').strip()
    if not message:
        return jsonify({'error': 'Mensagem vazia.'}), 400

    # Get conversation history from session
    history_key = f'chat_history_{current_user.id}'
    conversation_history = session.get(history_key, [])

    # Build context
    tenant_id = get_current_tenant_id()
    context = get_system_context(tenant_id)
    context['user_name'] = current_user.full_name
    context['user_role'] = current_user.role
    if current_user.tenant:
        context['tenant_name'] = current_user.tenant.name

    # Get AI response
    response = chat_assistant(message, context, conversation_history)

    # Update conversation history
    conversation_history.append({'role': 'user', 'content': message})
    conversation_history.append({'role': 'assistant', 'content': response})

    # Keep only last 20 messages
    session[history_key] = conversation_history[-20:]

    return jsonify({'response': response})


@ai_bp.route('/ai/chat/clear', methods=['POST'])
@login_required
@tenant_required
def clear_chat():
    """Clear chat history."""
    history_key = f'chat_history_{current_user.id}'
    session.pop(history_key, None)
    return jsonify({'success': True})


# --- Quick Actions from Project View ---

@ai_bp.route('/projects/<int:project_id>/ai-actions')
@login_required
@tenant_required
def project_ai_actions(project_id):
    """Show AI actions available for a project."""
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    return render_template('ai/project_actions.html', project=project, ai_configured=check_ai_configured())


# --- Proposal Generation ---

@ai_bp.route('/ai/proposal/<int:project_id>/<int:call_id>')
@login_required
@tenant_required
def proposal_page(project_id, call_id):
    """Page to generate proposal for a public call."""
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    call = PublicCall.query.get_or_404(call_id)

    return render_template('ai/proposal.html',
                           project=project,
                           call=call,
                           ai_configured=check_ai_configured())


@ai_bp.route('/ai/proposal/<int:project_id>/<int:call_id>/generate', methods=['POST'])
@login_required
@tenant_required
def generate_proposal(project_id, call_id):
    """Generate proposal content using AI."""
    if not check_ai_configured():
        return jsonify({'error': 'API de IA não configurada.'}), 400

    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    call = PublicCall.query.get_or_404(call_id)

    # Get additional info from request
    additional_info = request.json.get('additional_info', {})

    # Gather project data
    project_data = {
        'code': project.code,
        'title': project.title,
        'description': project.description,
        'category': project.category,
        'start_date': str(project.start_date) if project.start_date else None,
        'end_date': str(project.end_date) if project.end_date else None,
        'budget': project.budget,
        'funding_source': project.funding_source,
        'responsible': project.responsible.full_name if project.responsible else None,
        'milestones': [{
            'title': m.title,
            'description': m.description,
            'start_date': str(m.start_date),
            'end_date': str(m.end_date)
        } for m in project.milestones],
        'resources': [{
            'name': r.name,
            'type': r.type,
            'role': r.role
        } for r in project.resources]
    }

    # Gather call data
    call_data = {
        'source': call.source,
        'title': call.title,
        'theme': call.theme,
        'description': call.description,
        'deadline': call.deadline,
        'funding_source': call.funding_source,
        'target_audience': call.target_audience
    }

    # Get tenant info
    tenant = current_user.tenant
    company_info = {
        'name': tenant.name if tenant else 'Empresa',
        'cnpj': tenant.cnpj if tenant else additional_info.get('cnpj', ''),
    }

    # Merge additional info
    company_info.update(additional_info)

    # Generate proposal using AI
    from services.ai_service import get_anthropic_client
    client = get_anthropic_client()

    prompt = f"""Você é um especialista em elaboração de propostas para editais de P&D.
Gere uma proposta estruturada para o seguinte projeto se candidatar à chamada pública.

DADOS DA EMPRESA:
- Nome: {company_info.get('name', 'N/A')}
- CNPJ: {company_info.get('cnpj', 'N/A')}
- Área de Atuação: {company_info.get('area_atuacao', 'N/A')}
- Experiência em P&D: {company_info.get('experiencia_pd', 'N/A')}

DADOS DO PROJETO:
- Código: {project_data.get('code', 'N/A')}
- Título: {project_data.get('title', 'N/A')}
- Descrição: {project_data.get('description', 'N/A')}
- Categoria: {project_data.get('category', 'N/A')}
- Período: {project_data.get('start_date', 'N/A')} a {project_data.get('end_date', 'N/A')}
- Orçamento: R$ {project_data.get('budget', 0):,.2f}
- Responsável: {project_data.get('responsible', 'N/A')}

CHAMADA PÚBLICA:
- Fonte: {call_data.get('source', 'N/A')}
- Título: {call_data.get('title', 'N/A')}
- Tema: {call_data.get('theme', 'N/A')}
- Descrição: {call_data.get('description', 'N/A')}
- Prazo: {call_data.get('deadline', 'N/A')}
- Público-alvo: {call_data.get('target_audience', 'N/A')}

INFORMAÇÕES ADICIONAIS:
- Objetivo do Projeto: {company_info.get('objetivo_projeto', 'N/A')}
- Resultados Esperados: {company_info.get('resultados_esperados', 'N/A')}
- Metodologia: {company_info.get('metodologia', 'N/A')}
- Diferenciais: {company_info.get('diferenciais', 'N/A')}
- Impacto Esperado: {company_info.get('impacto', 'N/A')}

Gere uma proposta completa em formato markdown com as seguintes seções:

1. RESUMO EXECUTIVO (máx. 300 palavras)
2. IDENTIFICAÇÃO DO PROPONENTE
3. OBJETIVOS DO PROJETO (Geral e Específicos)
4. JUSTIFICATIVA E RELEVÂNCIA
5. METODOLOGIA
6. RESULTADOS ESPERADOS E METAS
7. CRONOGRAMA DE EXECUÇÃO
8. EQUIPE TÉCNICA
9. ORÇAMENTO DETALHADO
10. IMPACTOS ESPERADOS (Científico, Tecnológico, Econômico, Social)
11. RISCOS E ESTRATÉGIAS DE MITIGAÇÃO
12. CONSIDERAÇÕES FINAIS

Seja específico, profissional e alinhado com os requisitos da chamada.
Use linguagem técnica apropriada para editais de P&D.
"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=6000,
            messages=[{"role": "user", "content": prompt}]
        )

        proposal = response.content[0].text
        return jsonify({'proposal': proposal})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@ai_bp.route('/ai/proposal/<int:project_id>/<int:call_id>/questions', methods=['POST'])
@login_required
@tenant_required
def get_proposal_questions(project_id, call_id):
    """Get questions for additional info needed for proposal."""
    project = Project.query.get_or_404(project_id)
    ensure_tenant_access(project)

    call = PublicCall.query.get_or_404(call_id)
    tenant = current_user.tenant

    # Determine what info is missing
    questions = []

    if not tenant or not tenant.cnpj:
        questions.append({
            'field': 'cnpj',
            'label': 'CNPJ da Empresa',
            'type': 'text',
            'placeholder': '00.000.000/0000-00',
            'required': True
        })

    questions.extend([
        {
            'field': 'area_atuacao',
            'label': 'Área de Atuação da Empresa',
            'type': 'text',
            'placeholder': 'Ex: Tecnologia da Informação, Biotecnologia...',
            'required': True
        },
        {
            'field': 'experiencia_pd',
            'label': 'Experiência em P&D (breve descrição)',
            'type': 'textarea',
            'placeholder': 'Descreva projetos anteriores, parcerias com ICTs, patentes...',
            'required': False
        },
        {
            'field': 'objetivo_projeto',
            'label': 'Objetivo Principal do Projeto',
            'type': 'textarea',
            'placeholder': 'Qual o principal objetivo a ser alcançado?',
            'required': True
        },
        {
            'field': 'resultados_esperados',
            'label': 'Resultados Esperados',
            'type': 'textarea',
            'placeholder': 'Liste os principais resultados e entregas esperadas...',
            'required': True
        },
        {
            'field': 'metodologia',
            'label': 'Metodologia (resumo)',
            'type': 'textarea',
            'placeholder': 'Descreva brevemente a metodologia a ser utilizada...',
            'required': False
        },
        {
            'field': 'diferenciais',
            'label': 'Diferenciais e Inovação',
            'type': 'textarea',
            'placeholder': 'O que torna este projeto inovador?',
            'required': False
        },
        {
            'field': 'impacto',
            'label': 'Impacto Esperado',
            'type': 'textarea',
            'placeholder': 'Descreva o impacto científico, tecnológico, econômico e social...',
            'required': False
        }
    ])

    return jsonify({'questions': questions})
