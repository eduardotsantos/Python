"""
Routes for Orion Autônomos PMO - AI Agent Dashboard and API.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, make_response
from flask_login import login_required, current_user
from datetime import datetime, date
from io import BytesIO
import logging

from services.tenant_utils import tenant_required, get_current_tenant_id
from agents import PMOOrchestrator

logger = logging.getLogger(__name__)
pmo_agents_bp = Blueprint('pmo_agents', __name__, url_prefix='/pmo')


def get_orchestrator():
    """Get PMO Orchestrator for current tenant."""
    tenant_id = get_current_tenant_id()
    return PMOOrchestrator(tenant_id)


@pmo_agents_bp.route('/')
@login_required
@tenant_required
def dashboard():
    """Main PMO Agents dashboard."""
    orchestrator = get_orchestrator()
    agents_info = orchestrator.get_agent_info()

    return render_template('pmo_agents/dashboard.html',
        agents=agents_info,
        page_title='Orion Autônomos PMO'
    )


@pmo_agents_bp.route('/briefing')
@login_required
@tenant_required
def daily_briefing():
    """Generate and display daily executive briefing."""
    orchestrator = get_orchestrator()
    briefing = orchestrator.generate_daily_briefing(current_user.full_name)

    return render_template('pmo_agents/briefing.html',
        briefing=briefing,
        page_title='Briefing Executivo Diário'
    )


@pmo_agents_bp.route('/agent/<agent_name>')
@login_required
@tenant_required
def run_agent(agent_name):
    """Run a specific agent and show results."""
    project_id = request.args.get('project_id', type=int)

    orchestrator = get_orchestrator()
    agent = orchestrator.get_agent(agent_name)

    if not agent:
        flash('Agente não encontrado.', 'danger')
        return redirect(url_for('pmo_agents.dashboard'))

    result = orchestrator.run_agent(agent_name, project_id)

    return render_template('pmo_agents/agent_result.html',
        agent=agent,
        result=result,
        project_id=project_id,
        page_title=f'{agent.display_name} - Resultado'
    )


@pmo_agents_bp.route('/action-center')
@login_required
@tenant_required
def action_center():
    """Action center - view and execute suggested actions."""
    orchestrator = get_orchestrator()

    results = orchestrator.run_all_agents()

    all_actions = []
    for result in results:
        for action in result.actions:
            all_actions.append({
                'action': action,
                'agent_name': result.agent_name
            })

    all_actions.sort(key=lambda x: (
        0 if x['action'].priority.value == 'critical' else
        1 if x['action'].priority.value == 'high' else
        2 if x['action'].priority.value == 'medium' else 3
    ))

    return render_template('pmo_agents/action_center.html',
        actions=all_actions[:20],
        page_title='Central de Ações'
    )


@pmo_agents_bp.route('/minutes-parser', methods=['GET', 'POST'])
@login_required
@tenant_required
def minutes_parser():
    """Parse meeting minutes text."""
    from models import Project

    tenant_id = get_current_tenant_id()
    projects = Project.query.filter_by(tenant_id=tenant_id).all()

    extractions = None
    if request.method == 'POST':
        text = request.form.get('minutes_text', '')
        project_id = request.form.get('project_id', type=int)

        orchestrator = get_orchestrator()
        minutes_agent = orchestrator.get_agent('minutes_reader')

        if minutes_agent:
            extractions = minutes_agent.parse_text(text, project_id)

    return render_template('pmo_agents/minutes_parser.html',
        projects=projects,
        extractions=extractions,
        page_title='Leitor de Atas'
    )


# ============================================================================
# API ENDPOINTS
# ============================================================================

@pmo_agents_bp.route('/api/briefing')
@login_required
@tenant_required
def api_briefing():
    """API: Get daily briefing as JSON."""
    orchestrator = get_orchestrator()
    briefing = orchestrator.generate_daily_briefing(current_user.full_name)
    return jsonify(briefing.to_dict())


@pmo_agents_bp.route('/api/agent/<agent_name>')
@login_required
@tenant_required
def api_run_agent(agent_name):
    """API: Run a specific agent."""
    project_id = request.args.get('project_id', type=int)

    orchestrator = get_orchestrator()
    result = orchestrator.run_agent(agent_name, project_id)

    return jsonify(result.to_dict())


@pmo_agents_bp.route('/api/agents')
@login_required
@tenant_required
def api_list_agents():
    """API: List all available agents."""
    orchestrator = get_orchestrator()
    agents_info = orchestrator.get_agent_info()
    return jsonify({'agents': agents_info})


@pmo_agents_bp.route('/api/execute-action', methods=['POST'])
@login_required
@tenant_required
def api_execute_action():
    """API: Execute a suggested action."""
    from agents.base import ActionType, Severity, ActionSuggestion

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    action = ActionSuggestion(
        action_type=ActionType(data.get('action_type')),
        title=data.get('title', ''),
        description=data.get('description', ''),
        priority=Severity(data.get('priority', 'medium')),
        project_id=data.get('project_id'),
        data=data.get('data', {})
    )

    orchestrator = get_orchestrator()
    result = orchestrator.execute_action(action)

    return jsonify(result)


@pmo_agents_bp.route('/api/project/<int:project_id>/advice')
@login_required
@tenant_required
def api_project_advice(project_id):
    """API: Get AI advice for a specific project."""
    orchestrator = get_orchestrator()
    advisor = orchestrator.get_agent('advisor_agent')

    if advisor:
        advice = advisor.get_project_recommendation(project_id)
        return jsonify(advice)

    return jsonify({'error': 'Advisor agent not available'}), 500


@pmo_agents_bp.route('/api/parse-minutes', methods=['POST'])
@login_required
@tenant_required
def api_parse_minutes():
    """API: Parse meeting minutes text."""
    data = request.get_json()
    if not data or 'text' not in data:
        return jsonify({'error': 'No text provided'}), 400

    orchestrator = get_orchestrator()
    minutes_agent = orchestrator.get_agent('minutes_reader')

    if minutes_agent:
        extractions = minutes_agent.parse_text(
            data['text'],
            data.get('project_id')
        )
        return jsonify(extractions)

    return jsonify({'error': 'Minutes reader not available'}), 500


@pmo_agents_bp.route('/api/weekly-status')
@login_required
@tenant_required
def api_weekly_status():
    """API: Generate weekly status report."""
    project_id = request.args.get('project_id', type=int)

    orchestrator = get_orchestrator()
    comm_agent = orchestrator.get_agent('communication_agent')

    if comm_agent:
        report = comm_agent.generate_weekly_status(project_id)
        return jsonify({'report': report})

    return jsonify({'error': 'Communication agent not available'}), 500


@pmo_agents_bp.route('/api/financial-scenarios/<int:project_id>')
@login_required
@tenant_required
def api_financial_scenarios(project_id):
    """API: Generate financial scenarios for a project."""
    orchestrator = get_orchestrator()
    fin_agent = orchestrator.get_agent('financial_agent')

    if fin_agent:
        scenarios = fin_agent.generate_financial_scenarios(project_id)
        return jsonify({'scenarios': scenarios})

    return jsonify({'error': 'Financial agent not available'}), 500


@pmo_agents_bp.route('/api/replan-schedule/<int:project_id>')
@login_required
@tenant_required
def api_replan_schedule(project_id):
    """API: Get schedule replan suggestions."""
    orchestrator = get_orchestrator()
    sched_agent = orchestrator.get_agent('schedule_agent')

    if sched_agent:
        suggestions = sched_agent.suggest_replan(project_id)
        return jsonify(suggestions)

    return jsonify({'error': 'Schedule agent not available'}), 500


# ============================================================================
# PDF & EMAIL ENDPOINTS
# ============================================================================

@pmo_agents_bp.route('/briefing/pdf')
@login_required
@tenant_required
def briefing_pdf():
    """Generate and download briefing as PDF."""
    orchestrator = get_orchestrator()
    briefing = orchestrator.generate_daily_briefing(current_user.full_name)

    try:
        pdf_content = generate_briefing_pdf(briefing)
        response = make_response(pdf_content)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=briefing_{briefing.date.strftime("%Y%m%d")}.pdf'
        return response
    except ImportError:
        flash('Módulo de PDF não instalado. Execute: pip install reportlab', 'warning')
        return redirect(url_for('pmo_agents.daily_briefing'))
    except Exception as e:
        logger.error(f"Error generating PDF: {e}")
        flash(f'Erro ao gerar PDF: {str(e)}', 'danger')
        return redirect(url_for('pmo_agents.daily_briefing'))


@pmo_agents_bp.route('/briefing/email', methods=['POST'])
@login_required
@tenant_required
def briefing_email():
    """Send briefing via email to project resources."""
    from models import Resource, User, Project, Tenant

    tenant_id = get_current_tenant_id()
    tenant = Tenant.query.get(tenant_id)

    # Check if email is enabled for this tenant
    if not tenant or not tenant.email_enabled:
        flash('Envio de email não está habilitado para este tenant. Configure em Configurações.', 'warning')
        return redirect(url_for('pmo_agents.daily_briefing'))

    project_ids = request.form.getlist('project_ids', type=int)
    additional_emails = request.form.get('additional_emails', '')

    orchestrator = get_orchestrator()
    briefing = orchestrator.generate_daily_briefing(current_user.full_name)

    # Collect recipient emails (respecting user preferences)
    recipients = set()
    skipped_users = []

    def can_receive_briefing(user):
        """Check if user can receive briefing emails."""
        if not user or not user.email:
            return False
        # Check user preferences (default to True if field doesn't exist yet)
        email_notifications = getattr(user, 'email_notifications', True)
        email_briefing = getattr(user, 'email_briefing_daily', True)
        return email_notifications and email_briefing

    # Always add current user (if they have notifications enabled)
    if current_user.email and can_receive_briefing(current_user):
        recipients.add(current_user.email)

    if project_ids:
        # Get resources from selected projects
        for project_id in project_ids:
            project = Project.query.filter_by(
                id=project_id,
                tenant_id=tenant_id
            ).first()

            if project:
                # Add project responsible
                if project.responsible and can_receive_briefing(project.responsible):
                    recipients.add(project.responsible.email)
                elif project.responsible and project.responsible.email:
                    skipped_users.append(project.responsible.full_name)

                # Add all resources - try to match with users
                for resource in project.resources:
                    if resource.type in ['Humano', 'Pessoa', 'Human']:
                        user = User.query.filter(
                            User.tenant_id == tenant_id,
                            User.full_name.ilike(f'%{resource.name}%')
                        ).first()
                        if user and can_receive_briefing(user):
                            recipients.add(user.email)
                        elif user and user.email:
                            skipped_users.append(user.full_name)
    else:
        # Send to all active project responsibles
        projects = Project.query.filter_by(tenant_id=tenant_id).filter(
            Project.status.in_(['Em Execução', 'Em Andamento', 'Em execução', 'Planejamento', 'Ativo'])
        ).all()
        for project in projects:
            if project.responsible and can_receive_briefing(project.responsible):
                recipients.add(project.responsible.email)

        # Also add all active users with manager/admin role
        managers = User.query.filter(
            User.tenant_id == tenant_id,
            User.role.in_(['admin', 'manager']),
            User.active == True
        ).all()
        for manager in managers:
            if can_receive_briefing(manager):
                recipients.add(manager.email)
            elif manager.email:
                skipped_users.append(manager.full_name)

    # Add additional emails (always sent - manual override)
    if additional_emails:
        for email in additional_emails.split(','):
            email = email.strip()
            if '@' in email:
                recipients.add(email)

    # Log skipped users
    if skipped_users:
        logger.info(f"Users with notifications disabled: {skipped_users}")

    if not recipients:
        flash('Nenhum destinatário encontrado. Adicione emails manualmente.', 'warning')
        return redirect(url_for('pmo_agents.daily_briefing'))

    # Log recipients for debugging
    logger.info(f"Sending briefing to {len(recipients)} recipients: {recipients}")

    # Try to send email
    try:
        sent_count = send_briefing_email(briefing, list(recipients), tenant)
        flash(f'Briefing enviado para {sent_count} destinatário(s).', 'success')
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        flash(f'Erro ao enviar email: {str(e)}', 'danger')

    return redirect(url_for('pmo_agents.daily_briefing'))


@pmo_agents_bp.route('/api/briefing/recipients')
@login_required
@tenant_required
def api_briefing_recipients():
    """Get list of potential recipients for briefing email."""
    from models import Project, User

    tenant_id = get_current_tenant_id()
    recipients = []

    projects = Project.query.filter_by(tenant_id=tenant_id).filter(
        Project.status.in_(['Em Execução', 'Em Andamento', 'Em execução', 'Planejamento'])
    ).all()

    for project in projects:
        project_recipients = {
            'project_id': project.id,
            'project_code': project.code,
            'project_title': project.title,
            'emails': []
        }

        if project.responsible and project.responsible.email:
            project_recipients['emails'].append({
                'name': project.responsible.full_name,
                'email': project.responsible.email,
                'role': 'Responsável'
            })

        for resource in project.resources:
            if resource.type == 'Humano':
                user = User.query.filter(
                    User.tenant_id == tenant_id,
                    User.full_name.ilike(f'%{resource.name}%')
                ).first()
                if user and user.email:
                    project_recipients['emails'].append({
                        'name': user.full_name,
                        'email': user.email,
                        'role': resource.role or 'Recurso'
                    })

        if project_recipients['emails']:
            recipients.append(project_recipients)

    return jsonify({'recipients': recipients})


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def generate_briefing_pdf(briefing):
    """Generate PDF content for briefing."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib.enums import TA_CENTER, TA_LEFT

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1.5*cm, bottomMargin=1.5*cm)

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Title2', parent=styles['Heading1'], fontSize=18, textColor=colors.HexColor('#1a5276'), alignment=TA_CENTER))
    styles.add(ParagraphStyle(name='Section', parent=styles['Heading2'], fontSize=14, textColor=colors.HexColor('#2874a6'), spaceBefore=20))
    styles.add(ParagraphStyle(name='Normal2', parent=styles['Normal'], fontSize=10, leading=14))

    elements = []

    # Header
    elements.append(Paragraph("BRIEFING EXECUTIVO DIÁRIO", styles['Title2']))
    elements.append(Paragraph(f"Orion P&D - {briefing.date.strftime('%d/%m/%Y')}", styles['Normal']))
    elements.append(Spacer(1, 0.5*cm))

    # Status Banner
    status_colors = {
        'healthy': colors.HexColor('#27ae60'),
        'attention': colors.HexColor('#f39c12'),
        'critical': colors.HexColor('#e74c3c')
    }
    status_color = status_colors.get(briefing.overall_status.value, colors.gray)
    status_text = f"STATUS GERAL: {briefing.overall_status.value.upper()}"

    status_table = Table([[status_text]], colWidths=[18*cm])
    status_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), status_color),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 14),
        ('PADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(status_table)
    elements.append(Spacer(1, 0.5*cm))

    # Metrics Summary
    elements.append(Paragraph("MÉTRICAS DO DIA", styles['Section']))
    metrics_data = [
        ['Agentes Saudáveis', 'Atenção', 'Críticos', 'Total Insights'],
        [str(briefing.metrics.get('agents_healthy', 0)),
         str(briefing.metrics.get('agents_attention', 0)),
         str(briefing.metrics.get('agents_critical', 0)),
         str(briefing.metrics.get('total_insights', 0))]
    ]
    metrics_table = Table(metrics_data, colWidths=[4.5*cm, 4.5*cm, 4.5*cm, 4.5*cm])
    metrics_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#bdc3c7')),
        ('FONTSIZE', (0, 1), (-1, -1), 16),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(metrics_table)
    elements.append(Spacer(1, 0.5*cm))

    # Cost Analysis
    if briefing.cost_analysis:
        elements.append(Paragraph("ANÁLISE FINANCEIRA", styles['Section']))
        cost = briefing.cost_analysis
        cost_data = [
            ['Orçamento Total', 'Realizado', 'Variação', 'Mão de Obra'],
            [f"R$ {cost.get('total_budget', 0):,.2f}",
             f"R$ {cost.get('total_spent', 0):,.2f}",
             f"{cost.get('budget_variance', 0):+.1f}%",
             f"{cost.get('labor_percentage', 0):.1f}%"]
        ]
        cost_table = Table(cost_data, colWidths=[4.5*cm, 4.5*cm, 4.5*cm, 4.5*cm])
        cost_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#27ae60')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#bdc3c7')),
            ('PADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(cost_table)
        elements.append(Spacer(1, 0.3*cm))

    # Project Summaries
    if briefing.project_summaries:
        elements.append(Paragraph("RESUMO POR PROJETO", styles['Section']))
        proj_data = [['Projeto', 'Status', 'Progresso', 'Orçamento', 'Realizado', 'Variação']]

        for proj in briefing.project_summaries[:10]:
            status_emoji = '🟢' if proj.schedule_status == 'on_track' else '🟡' if proj.schedule_status == 'at_risk' else '🔴'
            proj_data.append([
                f"{proj.code}\n{proj.title[:30]}",
                f"{status_emoji} {proj.status}",
                f"{proj.progress:.0f}%",
                f"R$ {proj.budget:,.0f}",
                f"R$ {proj.spent:,.0f}",
                f"{proj.budget_variance:+.1f}%"
            ])

        proj_table = Table(proj_data, colWidths=[4*cm, 2.5*cm, 2*cm, 3*cm, 3*cm, 2*cm])
        proj_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#8e44ad')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdc3c7')),
            ('PADDING', (0, 0), (-1, -1), 5),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(proj_table)
        elements.append(Spacer(1, 0.3*cm))

    # Upcoming Activities
    if briefing.upcoming_activities:
        elements.append(PageBreak())
        elements.append(Paragraph("PRÓXIMAS ATIVIDADES (14 dias)", styles['Section']))
        upcoming_data = [['Atividade', 'Projeto', 'Prazo', 'Progresso', 'Custo Plan.', 'Custo Real.', 'Responsáveis']]

        for act in briefing.upcoming_activities[:12]:
            days_left = -act.days_variance
            deadline = f"{act.end_date.strftime('%d/%m')}\n({days_left}d)"
            upcoming_data.append([
                act.title[:25],
                act.project_name[:15],
                deadline,
                f"{act.progress}%",
                f"R$ {act.planned_cost:,.0f}",
                f"R$ {act.actual_cost:,.0f}",
                ', '.join(act.responsibles[:2])[:20]
            ])

        upcoming_table = Table(upcoming_data, colWidths=[3.5*cm, 2.5*cm, 1.8*cm, 1.5*cm, 2.2*cm, 2.2*cm, 3*cm])
        upcoming_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2980b9')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdc3c7')),
            ('PADDING', (0, 0), (-1, -1), 4),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(upcoming_table)
        elements.append(Spacer(1, 0.3*cm))

    # Past Activities with Cost Analysis
    if briefing.past_activities:
        elements.append(Paragraph("ATIVIDADES RECENTES (7 dias)", styles['Section']))
        past_data = [['Atividade', 'Projeto', 'Status', 'Hrs Plan.', 'Hrs Real.', 'Custo Plan.', 'Custo Real.', 'Var.']]

        for act in briefing.past_activities[:12]:
            status_icon = '⚠️' if act.is_late else '✓'
            variance_color = 'red' if act.cost_variance > 10 else 'green' if act.cost_variance < -10 else 'black'
            past_data.append([
                act.title[:25],
                act.project_name[:12],
                f"{status_icon} {act.status[:10]}",
                f"{act.planned_hours:.0f}h",
                f"{act.actual_hours:.0f}h",
                f"R$ {act.planned_cost:,.0f}",
                f"R$ {act.actual_cost:,.0f}",
                f"{act.cost_variance:+.0f}%"
            ])

        past_table = Table(past_data, colWidths=[3*cm, 2.2*cm, 2*cm, 1.5*cm, 1.5*cm, 2.2*cm, 2.2*cm, 1.5*cm])
        past_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#16a085')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdc3c7')),
            ('PADDING', (0, 0), (-1, -1), 4),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(past_table)
        elements.append(Spacer(1, 0.3*cm))

    # Priority Items
    if briefing.priority_items:
        elements.append(Paragraph("PRIORIDADES DO DIA", styles['Section']))
        for i, item in enumerate(briefing.priority_items[:5], 1):
            severity_icon = '🔴' if item['severity'] == 'critical' else '🟠' if item['severity'] == 'high' else '🟡'
            elements.append(Paragraph(
                f"<b>{i}. {severity_icon} {item['title']}</b><br/>"
                f"<font size=8>{item['description'][:150]}</font>",
                styles['Normal2']
            ))
            if item.get('recommendation'):
                elements.append(Paragraph(f"<font size=8 color='#2874a6'>💡 {item['recommendation']}</font>", styles['Normal']))
            elements.append(Spacer(1, 0.2*cm))

    # Footer
    elements.append(Spacer(1, 1*cm))
    elements.append(Paragraph(
        f"<font size=8 color='gray'>Gerado automaticamente pelo Orion PMO IA em {briefing.generated_at.strftime('%d/%m/%Y %H:%M')}</font>",
        styles['Normal']
    ))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


def send_briefing_email(briefing, recipients, tenant=None):
    """Send briefing email to recipients using tenant-specific or global config."""
    from flask_mail import Mail, Message
    from flask import current_app
    from app import mail as global_mail

    # Use tenant-specific mail config if available
    if tenant and tenant.mail_server and tenant.mail_username:
        # Create a new Mail instance with tenant config
        current_app.config['MAIL_SERVER'] = tenant.mail_server
        current_app.config['MAIL_PORT'] = tenant.mail_port or 587
        current_app.config['MAIL_USE_TLS'] = tenant.mail_use_tls
        current_app.config['MAIL_USE_SSL'] = tenant.mail_use_ssl
        current_app.config['MAIL_USERNAME'] = tenant.mail_username
        current_app.config['MAIL_PASSWORD'] = tenant.mail_password
        current_app.config['MAIL_DEFAULT_SENDER'] = tenant.mail_default_sender or tenant.mail_username

        mail = Mail(current_app)
        logger.info(f"Using tenant-specific email config: {tenant.mail_server}")
    else:
        mail = global_mail
        logger.info("Using global email config")

    # Generate HTML content
    html_content = generate_briefing_html(briefing)

    # Generate PDF attachment
    try:
        pdf_content = generate_briefing_pdf(briefing)
        has_pdf = True
    except:
        pdf_content = None
        has_pdf = False

    subject = f"📊 Briefing Executivo Diário - {briefing.date.strftime('%d/%m/%Y')}"

    sent_count = 0
    for recipient in recipients:
        try:
            msg = Message(
                subject=subject,
                recipients=[recipient],
                html=html_content
            )

            if has_pdf and pdf_content:
                msg.attach(
                    f"briefing_{briefing.date.strftime('%Y%m%d')}.pdf",
                    "application/pdf",
                    pdf_content
                )

            mail.send(msg)
            sent_count += 1
            logger.info(f"Briefing email sent to {recipient}")
        except Exception as e:
            logger.error(f"Failed to send email to {recipient}: {e}")

    return sent_count


def generate_briefing_html(briefing):
    """Generate HTML content for email."""
    status_colors = {
        'healthy': '#27ae60',
        'attention': '#f39c12',
        'critical': '#e74c3c'
    }
    status_color = status_colors.get(briefing.overall_status.value, '#95a5a6')

    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .header {{ background: linear-gradient(135deg, #1a5276, #2980b9); color: white; padding: 20px; text-align: center; }}
            .status-banner {{ background: {status_color}; color: white; padding: 15px; text-align: center; font-size: 18px; font-weight: bold; }}
            .section {{ margin: 20px; padding: 15px; background: #f8f9fa; border-radius: 8px; }}
            .section-title {{ color: #2874a6; font-size: 16px; font-weight: bold; margin-bottom: 10px; border-bottom: 2px solid #3498db; padding-bottom: 5px; }}
            table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
            th {{ background: #3498db; color: white; padding: 10px; text-align: left; }}
            td {{ padding: 8px; border-bottom: 1px solid #ddd; }}
            .metric-box {{ display: inline-block; width: 22%; text-align: center; padding: 15px; margin: 5px; background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            .metric-value {{ font-size: 24px; font-weight: bold; color: #2c3e50; }}
            .metric-label {{ font-size: 12px; color: #7f8c8d; }}
            .priority-item {{ background: white; padding: 10px; margin: 5px 0; border-left: 4px solid; border-radius: 4px; }}
            .critical {{ border-color: #e74c3c; }}
            .high {{ border-color: #f39c12; }}
            .footer {{ text-align: center; color: #7f8c8d; font-size: 12px; padding: 20px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>📊 Briefing Executivo Diário</h1>
            <p>Orion P&D - {briefing.date.strftime('%d/%m/%Y')}</p>
        </div>

        <div class="status-banner">
            STATUS GERAL: {briefing.overall_status.value.upper()}
        </div>

        <div class="section">
            <div class="section-title">📈 Métricas do Dia</div>
            <div style="text-align: center;">
                <div class="metric-box">
                    <div class="metric-value" style="color: #27ae60;">{briefing.metrics.get('agents_healthy', 0)}</div>
                    <div class="metric-label">Saudáveis</div>
                </div>
                <div class="metric-box">
                    <div class="metric-value" style="color: #f39c12;">{briefing.metrics.get('agents_attention', 0)}</div>
                    <div class="metric-label">Atenção</div>
                </div>
                <div class="metric-box">
                    <div class="metric-value" style="color: #e74c3c;">{briefing.metrics.get('agents_critical', 0)}</div>
                    <div class="metric-label">Críticos</div>
                </div>
                <div class="metric-box">
                    <div class="metric-value" style="color: #3498db;">{briefing.metrics.get('total_insights', 0)}</div>
                    <div class="metric-label">Insights</div>
                </div>
            </div>
        </div>
    """

    # Cost Analysis
    if briefing.cost_analysis:
        cost = briefing.cost_analysis
        variance_color = '#e74c3c' if cost.get('budget_variance', 0) > 10 else '#27ae60'
        html += f"""
        <div class="section">
            <div class="section-title">💰 Análise Financeira</div>
            <table>
                <tr>
                    <th>Orçamento Total</th>
                    <th>Realizado</th>
                    <th>Variação</th>
                    <th>Gasto do Mês</th>
                </tr>
                <tr>
                    <td>R$ {cost.get('total_budget', 0):,.2f}</td>
                    <td>R$ {cost.get('total_spent', 0):,.2f}</td>
                    <td style="color: {variance_color}; font-weight: bold;">{cost.get('budget_variance', 0):+.1f}%</td>
                    <td>R$ {cost.get('month_spent', 0):,.2f}</td>
                </tr>
            </table>
        </div>
        """

    # Upcoming Activities
    if briefing.upcoming_activities:
        html += """
        <div class="section">
            <div class="section-title">📅 Próximas Atividades (14 dias)</div>
            <table>
                <tr>
                    <th>Atividade</th>
                    <th>Projeto</th>
                    <th>Prazo</th>
                    <th>Progresso</th>
                    <th>Custo Planejado</th>
                    <th>Custo Realizado</th>
                </tr>
        """
        for act in briefing.upcoming_activities[:8]:
            days_left = -act.days_variance
            html += f"""
                <tr>
                    <td>{act.title[:40]}</td>
                    <td>{act.project_name[:20]}</td>
                    <td>{act.end_date.strftime('%d/%m')} ({days_left}d)</td>
                    <td>{act.progress}%</td>
                    <td>R$ {act.planned_cost:,.0f}</td>
                    <td>R$ {act.actual_cost:,.0f}</td>
                </tr>
            """
        html += "</table></div>"

    # Priority Items
    if briefing.priority_items:
        html += """
        <div class="section">
            <div class="section-title">🎯 Prioridades do Dia</div>
        """
        for item in briefing.priority_items[:5]:
            severity_class = 'critical' if item['severity'] == 'critical' else 'high'
            icon = '🔴' if item['severity'] == 'critical' else '🟠'
            html += f"""
            <div class="priority-item {severity_class}">
                <strong>{icon} {item['title']}</strong><br/>
                <small>{item['description'][:150]}</small>
                {f"<br/><em style='color: #2874a6;'>💡 {item['recommendation']}</em>" if item.get('recommendation') else ""}
            </div>
            """
        html += "</div>"

    html += f"""
        <div class="footer">
            <p>Gerado automaticamente pelo Orion PMO IA em {briefing.generated_at.strftime('%d/%m/%Y %H:%M')}</p>
            <p>Este é um email automático. Acesse o sistema para mais detalhes.</p>
        </div>
    </body>
    </html>
    """

    return html
