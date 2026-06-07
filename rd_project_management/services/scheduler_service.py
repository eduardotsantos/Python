"""
Scheduler Service - Automated tasks like daily briefing emails.
Uses APScheduler for background task scheduling.
"""
import logging
from datetime import datetime, date
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def send_daily_briefings():
    """
    Send daily briefing emails to all enabled tenants and users.
    Runs at 7:00 AM every day.
    """
    from flask import current_app
    from models import Tenant, User, Project, db
    from agents.orchestrator import PMOOrchestrator

    logger.info("=" * 50)
    logger.info("Starting automated daily briefing distribution")
    logger.info("=" * 50)

    try:
        # Get all active tenants with email enabled
        tenants = Tenant.query.filter_by(active=True, email_enabled=True).all()
        logger.info(f"Found {len(tenants)} tenants with email enabled")

        for tenant in tenants:
            try:
                send_tenant_briefing(tenant)
            except Exception as e:
                logger.error(f"Error sending briefing for tenant {tenant.name}: {e}")

        logger.info("Daily briefing distribution completed")

    except Exception as e:
        logger.error(f"Error in daily briefing scheduler: {e}")


def send_tenant_briefing(tenant):
    """Send briefing to all eligible users of a tenant."""
    from flask import current_app
    from flask_mail import Mail, Message
    from models import User, Project
    from agents.orchestrator import PMOOrchestrator

    logger.info(f"Processing tenant: {tenant.name}")

    # Check SMTP configuration
    if not tenant.mail_server or not tenant.mail_username:
        logger.warning(f"Tenant {tenant.name} has no SMTP configuration, skipping")
        return

    # Get users who want daily briefing
    recipients = User.query.filter_by(
        tenant_id=tenant.id,
        active=True,
        email_notifications=True,
        email_briefing_daily=True
    ).all()

    if not recipients:
        logger.info(f"No recipients for tenant {tenant.name}")
        return

    logger.info(f"Found {len(recipients)} recipients for tenant {tenant.name}")

    # Get active projects for this tenant
    projects = Project.query.filter_by(tenant_id=tenant.id).filter(
        Project.status.in_(['Em Execução', 'Em Andamento', 'Em execução', 'Planejamento'])
    ).all()

    if not projects:
        logger.info(f"No active projects for tenant {tenant.name}, skipping briefing")
        return

    # Generate briefing
    try:
        orchestrator = PMOOrchestrator(tenant_id=tenant.id)
        briefing = orchestrator.generate_daily_briefing()
    except Exception as e:
        logger.error(f"Error generating briefing for tenant {tenant.name}: {e}")
        return

    # Configure mail
    port = tenant.mail_port or 587
    if port == 465:
        use_ssl, use_tls = True, False
    else:
        use_ssl, use_tls = False, True

    current_app.config['MAIL_SERVER'] = tenant.mail_server
    current_app.config['MAIL_PORT'] = port
    current_app.config['MAIL_USE_TLS'] = use_tls
    current_app.config['MAIL_USE_SSL'] = use_ssl
    current_app.config['MAIL_USERNAME'] = tenant.mail_username
    current_app.config['MAIL_PASSWORD'] = tenant.mail_password
    current_app.config['MAIL_DEFAULT_SENDER'] = tenant.mail_default_sender or tenant.mail_username

    mail = Mail(current_app)

    # Generate email content
    html_content = generate_briefing_html(briefing, tenant)
    pdf_content = generate_briefing_pdf(briefing)

    subject = f"📊 Briefing Executivo Diário - {briefing.date.strftime('%d/%m/%Y')}"

    # Send to each recipient
    sent_count = 0
    for user in recipients:
        try:
            msg = Message(
                subject=subject,
                recipients=[user.email],
                html=html_content
            )

            if pdf_content:
                msg.attach(
                    f"briefing_{briefing.date.strftime('%Y%m%d')}.pdf",
                    'application/pdf',
                    pdf_content
                )

            mail.send(msg)
            sent_count += 1
            logger.info(f"Briefing sent to {user.email}")

        except Exception as e:
            logger.error(f"Failed to send briefing to {user.email}: {e}")

    logger.info(f"Tenant {tenant.name}: sent {sent_count}/{len(recipients)} briefings")


def generate_briefing_html(briefing, tenant):
    """Generate HTML content for briefing email."""
    status_colors = {
        'healthy': '#27ae60',
        'attention': '#f39c12',
        'critical': '#e74c3c'
    }
    status_color = status_colors.get(briefing.overall_status.value, '#95a5a6')

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .header {{ background: linear-gradient(135deg, #1a237e 0%, #3949ab 100%); color: white; padding: 30px; text-align: center; }}
            .header h1 {{ margin: 0; font-size: 24px; }}
            .header p {{ margin: 10px 0 0; opacity: 0.9; }}
            .status-banner {{ background: {status_color}; color: white; padding: 15px; text-align: center; font-size: 18px; font-weight: bold; }}
            .content {{ padding: 20px; max-width: 800px; margin: 0 auto; }}
            .section {{ background: #f5f5f5; border-radius: 8px; padding: 20px; margin-bottom: 20px; }}
            .section h2 {{ color: #1a237e; margin-top: 0; font-size: 18px; border-bottom: 2px solid #1a237e; padding-bottom: 10px; }}
            .metric {{ display: inline-block; text-align: center; padding: 15px; margin: 5px; background: white; border-radius: 8px; min-width: 100px; }}
            .metric-value {{ font-size: 28px; font-weight: bold; color: #1a237e; }}
            .metric-label {{ font-size: 12px; color: #666; }}
            .alert {{ padding: 15px; border-radius: 8px; margin: 10px 0; }}
            .alert-critical {{ background: #ffebee; border-left: 4px solid #f44336; }}
            .alert-warning {{ background: #fff3e0; border-left: 4px solid #ff9800; }}
            .alert-info {{ background: #e3f2fd; border-left: 4px solid #2196f3; }}
            .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
            ul {{ padding-left: 20px; }}
            li {{ margin-bottom: 8px; }}
            table {{ width: 100%; border-collapse: collapse; }}
            th {{ background: #1a237e; color: white; padding: 10px; text-align: left; }}
            td {{ padding: 8px; border-bottom: 1px solid #ddd; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>📊 Briefing Executivo Diário</h1>
            <p>{tenant.name} - {briefing.date.strftime('%d/%m/%Y')}</p>
        </div>

        <div class="status-banner">
            STATUS GERAL: {briefing.overall_status.value.upper()}
        </div>

        <div class="content">
            <div class="section">
                <h2>📈 Métricas do Dia</h2>
                <div style="text-align: center;">
                    <div class="metric">
                        <div class="metric-value" style="color: #27ae60;">{briefing.metrics.get('agents_healthy', 0)}</div>
                        <div class="metric-label">Saudáveis</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value" style="color: #f39c12;">{briefing.metrics.get('agents_attention', 0)}</div>
                        <div class="metric-label">Atenção</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value" style="color: #e74c3c;">{briefing.metrics.get('agents_critical', 0)}</div>
                        <div class="metric-label">Críticos</div>
                    </div>
                    <div class="metric">
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
                <h2>💰 Análise Financeira</h2>
                <table>
                    <tr>
                        <th>Orçamento Total</th>
                        <th>Realizado</th>
                        <th>Variação</th>
                    </tr>
                    <tr>
                        <td>R$ {cost.get('total_budget', 0):,.2f}</td>
                        <td>R$ {cost.get('total_spent', 0):,.2f}</td>
                        <td style="color: {variance_color}; font-weight: bold;">{cost.get('budget_variance', 0):+.1f}%</td>
                    </tr>
                </table>
            </div>
        """

    # PMBOK 8 - Value Delivery Summary
    if briefing.project_summaries:
        total_expected = sum(p.expected_value for p in briefing.project_summaries if hasattr(p, 'expected_value') and p.expected_value)
        total_realized = sum(p.realized_value for p in briefing.project_summaries if hasattr(p, 'realized_value') and p.realized_value)
        value_capture_pct = (total_realized / total_expected * 100) if total_expected > 0 else 0
        projects_with_value = [p for p in briefing.project_summaries if hasattr(p, 'expected_value') and p.expected_value and p.expected_value > 0]

        if total_expected > 0:
            html += f"""
            <div class="section">
                <h2>🏆 Entrega de Valor (PMBOK 8)</h2>
                <table>
                    <tr>
                        <th>Valor Esperado</th>
                        <th>Valor Realizado</th>
                        <th>Captura</th>
                    </tr>
                    <tr>
                        <td>R$ {total_expected:,.2f}</td>
                        <td style="color: #27ae60; font-weight: bold;">R$ {total_realized:,.2f}</td>
                        <td style="color: {'#27ae60' if value_capture_pct >= 80 else '#f39c12' if value_capture_pct >= 50 else '#e74c3c'}; font-weight: bold;">{value_capture_pct:.0f}%</td>
                    </tr>
                </table>
            """
            # Projects needing value capture attention
            pending_value_projects = [p for p in projects_with_value if hasattr(p, 'value_status') and p.value_status in ['Não iniciado', 'Em captura']]
            if pending_value_projects:
                html += "<h4 style='color: #f39c12; margin-top: 15px;'>💡 Projetos pendentes de captura de valor:</h4><ul>"
                for proj in pending_value_projects[:5]:
                    html += f"<li><strong>{proj.code}</strong>: {proj.title[:40]} (R$ {proj.expected_value:,.2f})</li>"
                html += "</ul>"
            html += "</div>"

    # Compliance Summary
    if briefing.compliance_summary:
        comp = briefing.compliance_summary
        comp_dict = comp.to_dict() if hasattr(comp, 'to_dict') else comp
        html += f"""
            <div class="section">
                <h2>🛡️ Conformidade</h2>
                <div style="text-align: center;">
                    <div class="metric">
                        <div class="metric-value" style="color: {'#e74c3c' if comp_dict.get('open_risks', 0) > 0 else '#27ae60'};">{comp_dict.get('open_risks', 0)}</div>
                        <div class="metric-label">Riscos Abertos</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value" style="color: {'#e74c3c' if comp_dict.get('overdue_pending', 0) > 0 else '#27ae60'};">{comp_dict.get('overdue_pending', 0)}</div>
                        <div class="metric-label">Pendências Atrasadas</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value" style="color: {'#e74c3c' if comp_dict.get('open_bugs', 0) > 0 else '#27ae60'};">{comp_dict.get('open_bugs', 0)}</div>
                        <div class="metric-label">Bugs Abertos</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value" style="color: {'#f39c12' if comp_dict.get('open_ncs', 0) > 0 else '#27ae60'};">{comp_dict.get('open_ncs', 0)}</div>
                        <div class="metric-label">NCs Abertas</div>
                    </div>
                </div>
        """
        # Critical items list
        critical_items = comp_dict.get('critical_items', [])
        if critical_items:
            html += "<h4 style='color: #e74c3c; margin-top: 15px;'>⚠️ Itens Críticos:</h4><ul>"
            for item in critical_items[:5]:
                html += f"<li><strong>{item.get('type', '')}</strong>: {item.get('title', '')} - {item.get('project', '')}</li>"
            html += "</ul>"
        html += "</div>"

    # Upcoming Activities
    if briefing.upcoming_activities:
        html += """
            <div class="section">
                <h2>📅 Próximas Atividades (14 dias)</h2>
                <table>
                    <tr>
                        <th>Atividade</th>
                        <th>Projeto</th>
                        <th>Prazo</th>
                        <th>Progresso</th>
                    </tr>
        """
        for act in briefing.upcoming_activities[:8]:
            days_left = -act.days_variance if hasattr(act, 'days_variance') else 0
            html += f"""
                <tr>
                    <td>{act.title[:40]}</td>
                    <td>{act.project_name[:20]}</td>
                    <td>{act.end_date.strftime('%d/%m')} ({days_left}d)</td>
                    <td>{act.progress}%</td>
                </tr>
            """
        html += "</table></div>"

    # Priority Items
    if briefing.priority_items:
        html += """
            <div class="section">
                <h2>🎯 Prioridades do Dia</h2>
        """
        for item in briefing.priority_items[:5]:
            severity_class = 'alert-critical' if item.get('severity') == 'critical' else 'alert-warning'
            icon = '🔴' if item.get('severity') == 'critical' else '🟠'
            html += f"""
                <div class="alert {severity_class}">
                    <strong>{icon} {item.get('title', '')}</strong><br/>
                    <small>{item.get('description', '')[:150]}</small>
                    {f"<br/><em style='color: #1a237e;'>💡 {item.get('recommendation', '')}</em>" if item.get('recommendation') else ""}
                </div>
            """
        html += "</div>"

    # Recommended Actions
    if briefing.recommended_actions:
        html += """
            <div class="section">
                <h2>⚡ Ações Recomendadas</h2>
        """
        for action in briefing.recommended_actions[:8]:
            priority_color = '#e74c3c' if action.priority.value == 'critical' else '#f39c12' if action.priority.value == 'high' else '#2196f3'
            html += f"""
                <div class="alert" style="border-left: 4px solid {priority_color}; background: white;">
                    <strong>{action.title}</strong><br/>
                    <small>{action.description[:200]}</small>
                </div>
            """
        html += "</div>"

    html += f"""
            <div class="footer">
                <p>Orion Autonomous PMO - Sistema de Gestão de Projetos P&D</p>
                <p>Este email foi enviado automaticamente às 7:00.</p>
                <p><small>Para desativar, acesse seu perfil e desmarque "Briefing diário".</small></p>
            </div>
        </div>
    </body>
    </html>
    """

    return html


def generate_briefing_pdf(briefing):
    """Generate PDF for briefing attachment."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.units import cm
        from io import BytesIO

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
        styles = getSampleStyleSheet()
        story = []

        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#1a237e'),
            spaceAfter=20
        )
        section_style = ParagraphStyle(
            'SectionTitle',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#1a237e'),
            spaceBefore=15,
            spaceAfter=10
        )

        # Title
        story.append(Paragraph(f"Briefing Executivo - {briefing.date.strftime('%d/%m/%Y')}", title_style))
        story.append(Spacer(1, 10))

        # Executive Summary
        status_color = '#28a745' if briefing.overall_status.value == 'healthy' else '#ffc107' if briefing.overall_status.value == 'attention' else '#dc3545'
        story.append(Paragraph(f"<b>Status Geral:</b> <font color='{status_color}'>{briefing.overall_status.value.upper()}</font>", styles['Normal']))
        story.append(Spacer(1, 10))

        # Metrics summary table
        metrics = briefing.metrics if briefing.metrics else {}
        total_projects = metrics.get('total_projects', len(briefing.project_summaries))
        healthy = metrics.get('healthy_projects', 0)
        at_risk = metrics.get('at_risk_projects', 0)
        critical = metrics.get('critical_projects', 0)

        summary_data = [
            ['Métrica', 'Valor'],
            ['Total de Projetos', str(total_projects)],
            ['Projetos Saudáveis', str(healthy)],
            ['Projetos em Risco', str(at_risk)],
            ['Projetos Críticos', str(critical)],
        ]

        table = Table(summary_data, colWidths=[10*cm, 5*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a237e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f5f5f5')),
            ('GRID', (0, 0), (-1, -1), 1, colors.white),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ]))
        story.append(table)
        story.append(Spacer(1, 20))

        # PMBOK 8 - Value Delivery Section
        if briefing.project_summaries:
            total_expected = sum(p.expected_value for p in briefing.project_summaries if hasattr(p, 'expected_value') and p.expected_value)
            total_realized = sum(p.realized_value for p in briefing.project_summaries if hasattr(p, 'realized_value') and p.realized_value)

            if total_expected > 0:
                value_capture_pct = (total_realized / total_expected * 100) if total_expected > 0 else 0
                story.append(Paragraph("Entrega de Valor (PMBOK 8)", section_style))

                value_data = [
                    ['Métrica', 'Valor'],
                    ['Valor Esperado (Total)', f'R$ {total_expected:,.2f}'],
                    ['Valor Realizado', f'R$ {total_realized:,.2f}'],
                    ['Captura de Valor', f'{value_capture_pct:.0f}%'],
                ]

                value_table = Table(value_data, colWidths=[10*cm, 5*cm])
                value_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#17a2b8')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#e3f2fd')),
                    ('GRID', (0, 0), (-1, -1), 1, colors.white),
                    ('FONTSIZE', (0, 1), (-1, -1), 10),
                    ('TOPPADDING', (0, 1), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
                ]))
                story.append(value_table)
                story.append(Spacer(1, 20))

        # Compliance Summary Section
        compliance = briefing.compliance_summary
        if compliance and (compliance.open_risks > 0 or compliance.overdue_pending > 0 or
                          compliance.open_bugs > 0 or compliance.open_ncs > 0):
            story.append(Paragraph("Resumo de Conformidade", section_style))

            compliance_data = [
                ['Item', 'Total', 'Abertos/Atrasados', 'Críticos'],
                ['Riscos', str(compliance.total_risks), str(compliance.open_risks), str(compliance.critical_risks)],
                ['Pendências', str(compliance.total_pending), str(compliance.overdue_pending), '-'],
                ['Bugs', str(compliance.total_bugs), str(compliance.open_bugs), str(compliance.critical_bugs)],
                ['Não Conformidades', str(compliance.total_ncs), str(compliance.open_ncs), '-'],
                ['Ações Corretivas', str(compliance.total_actions), str(compliance.pending_actions), '-'],
            ]

            compliance_table = Table(compliance_data, colWidths=[6*cm, 3*cm, 4*cm, 3*cm])
            compliance_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dc3545')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#fff5f5')),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#ffcccc')),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('TOPPADDING', (0, 1), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ]))
            story.append(compliance_table)
            story.append(Spacer(1, 15))

            # Critical Items List
            if compliance.critical_items:
                story.append(Paragraph("<b>Itens Críticos:</b>", styles['Normal']))
                for item in compliance.critical_items[:10]:
                    item_text = f"• [{item.get('type', 'Item')}] {item.get('title', 'Sem título')} - {item.get('project', 'Sem projeto')}"
                    story.append(Paragraph(item_text, styles['Normal']))
                story.append(Spacer(1, 10))

        # Recommended Actions Section
        if briefing.recommended_actions:
            story.append(Paragraph("Ações Recomendadas", section_style))

            for i, action in enumerate(briefing.recommended_actions[:10], 1):
                priority = action.priority.value if hasattr(action.priority, 'value') else str(action.priority)
                priority_color = '#dc3545' if priority == 'critical' else '#ffc107' if priority == 'high' else '#17a2b8'

                action_text = f"<b>{i}. [{priority.upper()}]</b> {action.title}"
                story.append(Paragraph(action_text, styles['Normal']))
                if action.description:
                    desc_style = ParagraphStyle('Desc', parent=styles['Normal'], leftIndent=20, fontSize=9, textColor=colors.gray)
                    story.append(Paragraph(action.description[:200], desc_style))
                story.append(Spacer(1, 5))
            story.append(Spacer(1, 10))

        # Priority Items
        if briefing.priority_items:
            story.append(Paragraph("Itens Prioritários", section_style))
            for item in briefing.priority_items[:8]:
                if isinstance(item, dict):
                    item_text = f"• {item.get('title', item.get('description', str(item)))}"
                else:
                    item_text = f"• {str(item)}"
                story.append(Paragraph(item_text, styles['Normal']))
            story.append(Spacer(1, 10))

        # Project Summaries
        if briefing.project_summaries:
            story.append(Paragraph("Resumo dos Projetos", section_style))
            for proj in briefing.project_summaries[:10]:
                status_indicator = "●" if proj.health_status.value == 'healthy' else "◐" if proj.health_status.value == 'attention' else "○"
                proj_text = f"{status_indicator} <b>{proj.code}</b> - {proj.title}"
                story.append(Paragraph(proj_text, styles['Normal']))
                if proj.next_milestone:
                    detail_style = ParagraphStyle('Detail', parent=styles['Normal'], leftIndent=20, fontSize=9, textColor=colors.gray)
                    story.append(Paragraph(f"Próximo marco: {proj.next_milestone}", detail_style))
            story.append(Spacer(1, 10))

        # Cost Analysis
        if briefing.cost_analysis:
            story.append(Paragraph("Análise de Custos", section_style))
            cost = briefing.cost_analysis
            cost_text = f"Orçamento Total: R$ {cost.get('total_budget', 0):,.2f} | Executado: R$ {cost.get('total_spent', 0):,.2f}"
            story.append(Paragraph(cost_text, styles['Normal']))
            if cost.get('over_budget_projects'):
                story.append(Paragraph(f"<font color='red'>Projetos acima do orçamento: {len(cost.get('over_budget_projects', []))}</font>", styles['Normal']))

        doc.build(story)
        return buffer.getvalue()

    except Exception as e:
        logger.error(f"Error generating PDF: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


def init_scheduler(app):
    """Initialize the scheduler with the Flask app context."""

    def run_with_context():
        with app.app_context():
            send_daily_briefings()

    # Schedule daily briefing at 7:00 AM
    scheduler.add_job(
        run_with_context,
        CronTrigger(hour=7, minute=0),
        id='daily_briefing',
        name='Daily Executive Briefing',
        replace_existing=True
    )

    # Start the scheduler
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started - Daily briefing scheduled for 7:00 AM")

    return scheduler
