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
            .content {{ padding: 20px; max-width: 800px; margin: 0 auto; }}
            .section {{ background: #f5f5f5; border-radius: 8px; padding: 20px; margin-bottom: 20px; }}
            .section h2 {{ color: #1a237e; margin-top: 0; font-size: 18px; border-bottom: 2px solid #1a237e; padding-bottom: 10px; }}
            .metric {{ display: inline-block; text-align: center; padding: 15px; margin: 5px; background: white; border-radius: 8px; min-width: 120px; }}
            .metric-value {{ font-size: 28px; font-weight: bold; color: #1a237e; }}
            .metric-label {{ font-size: 12px; color: #666; }}
            .alert {{ padding: 15px; border-radius: 8px; margin: 10px 0; }}
            .alert-critical {{ background: #ffebee; border-left: 4px solid #f44336; }}
            .alert-warning {{ background: #fff3e0; border-left: 4px solid #ff9800; }}
            .alert-info {{ background: #e3f2fd; border-left: 4px solid #2196f3; }}
            .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
            ul {{ padding-left: 20px; }}
            li {{ margin-bottom: 8px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>📊 Briefing Executivo Diário</h1>
            <p>{tenant.name} - {briefing.date.strftime('%d/%m/%Y')}</p>
        </div>
        <div class="content">
            <div class="section">
                <h2>📈 Visão Geral do Portfólio</h2>
                <div style="text-align: center;">
                    <div class="metric">
                        <div class="metric-value">{briefing.total_projects}</div>
                        <div class="metric-label">Projetos Ativos</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{briefing.health_summary.get('healthy', 0)}</div>
                        <div class="metric-label">Saudáveis</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{briefing.health_summary.get('at_risk', 0)}</div>
                        <div class="metric-label">Em Risco</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{briefing.health_summary.get('critical', 0)}</div>
                        <div class="metric-label">Críticos</div>
                    </div>
                </div>
            </div>
    """

    # Critical alerts
    if briefing.critical_alerts:
        html += """
            <div class="section">
                <h2>🔴 Alertas Críticos</h2>
        """
        for alert in briefing.critical_alerts[:5]:
            html += f"""
                <div class="alert alert-critical">
                    <strong>{alert.get('title', 'Alerta')}</strong><br>
                    {alert.get('description', '')}
                </div>
            """
        html += "</div>"

    # Key insights
    if briefing.key_insights:
        html += """
            <div class="section">
                <h2>💡 Principais Insights</h2>
                <ul>
        """
        for insight in briefing.key_insights[:5]:
            html += f"<li>{insight}</li>"
        html += "</ul></div>"

    # Today's priorities
    if briefing.todays_priorities:
        html += """
            <div class="section">
                <h2>🎯 Prioridades de Hoje</h2>
                <ul>
        """
        for priority in briefing.todays_priorities[:5]:
            html += f"<li>{priority}</li>"
        html += "</ul></div>"

    html += f"""
            <div class="footer">
                <p>Orion PMO - Sistema de Gestão de Projetos P&D</p>
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

        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#1a237e'),
            spaceAfter=20
        )
        story.append(Paragraph(f"Briefing Executivo - {briefing.date.strftime('%d/%m/%Y')}", title_style))
        story.append(Spacer(1, 20))

        # Summary table
        summary_data = [
            ['Métrica', 'Valor'],
            ['Total de Projetos', str(briefing.total_projects)],
            ['Projetos Saudáveis', str(briefing.health_summary.get('healthy', 0))],
            ['Projetos em Risco', str(briefing.health_summary.get('at_risk', 0))],
            ['Projetos Críticos', str(briefing.health_summary.get('critical', 0))],
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

        # Insights
        if briefing.key_insights:
            story.append(Paragraph("Principais Insights", styles['Heading2']))
            for insight in briefing.key_insights[:5]:
                story.append(Paragraph(f"• {insight}", styles['Normal']))
            story.append(Spacer(1, 15))

        # Priorities
        if briefing.todays_priorities:
            story.append(Paragraph("Prioridades de Hoje", styles['Heading2']))
            for priority in briefing.todays_priorities[:5]:
                story.append(Paragraph(f"• {priority}", styles['Normal']))

        doc.build(story)
        return buffer.getvalue()

    except Exception as e:
        logger.error(f"Error generating PDF: {e}")
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
