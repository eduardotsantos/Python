"""
Email service using per-tenant SMTP configuration.
"""
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


def send_email_via_tenant(tenant, to_email, subject, html_body, text_body=None):
    """
    Send an email using the tenant's SMTP configuration.
    Returns (success: bool, error_message: str|None).
    """
    if not tenant or not tenant.email_enabled:
        return False, "Email not enabled for this tenant"

    if not tenant.mail_server or not tenant.mail_username or not tenant.mail_password:
        return False, "Incomplete SMTP configuration"

    sender = tenant.mail_default_sender or tenant.mail_username

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = to_email

    if text_body:
        msg.attach(MIMEText(text_body, 'plain', 'utf-8'))
    msg.attach(MIMEText(html_body, 'html', 'utf-8'))

    try:
        port = tenant.mail_port or 587
        use_ssl = tenant.mail_use_ssl
        use_tls = tenant.mail_use_tls

        if use_ssl:
            server = smtplib.SMTP_SSL(tenant.mail_server, port)
        else:
            server = smtplib.SMTP(tenant.mail_server, port)
            if use_tls:
                server.starttls()

        server.login(tenant.mail_username, tenant.mail_password)
        server.sendmail(sender, [to_email], msg.as_string())
        server.quit()
        logger.info(f"Email sent to {to_email} via tenant {tenant.name}")
        return True, None
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False, str(e)


def send_password_reset_email(user, reset_url):
    """Send a password reset email to the user using their tenant's SMTP settings."""
    tenant = user.tenant if user.tenant_id else None

    subject = "Redefinição de Senha - Orion P&D"

    html_body = f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="font-family: 'Segoe UI', sans-serif; background:#f5f5f5; margin:0; padding:20px;">
  <div style="max-width:500px; margin:0 auto; background:#fff; border-radius:12px; overflow:hidden; box-shadow:0 4px 20px rgba(0,0,0,0.1);">
    <div style="background:linear-gradient(135deg,#0066cc,#00d4aa); padding:32px; text-align:center;">
      <h1 style="color:#fff; margin:0; font-size:1.5rem;">&#11088; Orion P&amp;D</h1>
      <p style="color:rgba(255,255,255,0.85); margin:8px 0 0;">Plataforma de Gestão de Inovação</p>
    </div>
    <div style="padding:32px;">
      <h2 style="color:#333; margin-top:0;">Redefinição de Senha</h2>
      <p style="color:#555;">Olá, <strong>{user.full_name}</strong>!</p>
      <p style="color:#555;">Recebemos uma solicitação para redefinir a senha da sua conta. Clique no botão abaixo para criar uma nova senha:</p>
      <div style="text-align:center; margin:32px 0;">
        <a href="{reset_url}" style="background:linear-gradient(135deg,#0066cc,#00d4aa); color:#fff; padding:14px 32px; border-radius:8px; text-decoration:none; font-weight:600; display:inline-block;">
          Redefinir Minha Senha
        </a>
      </div>
      <p style="color:#888; font-size:0.85rem;">Este link é válido por <strong>1 hora</strong>. Após esse prazo, você precisará solicitar um novo link.</p>
      <p style="color:#888; font-size:0.85rem;">Se você não solicitou a redefinição de senha, ignore este email. Sua conta permanecerá segura.</p>
      <hr style="border:none; border-top:1px solid #eee; margin:24px 0;">
      <p style="color:#aaa; font-size:0.8rem; text-align:center;">
        Se o botão não funcionar, copie e cole este link no seu navegador:<br>
        <a href="{reset_url}" style="color:#0066cc; word-break:break-all;">{reset_url}</a>
      </p>
    </div>
    <div style="background:#f9f9f9; padding:16px; text-align:center; border-top:1px solid #eee;">
      <p style="color:#aaa; font-size:0.8rem; margin:0;">Orion P&amp;D - Gestão de Projetos de Inovação</p>
    </div>
  </div>
</body>
</html>
"""
    text_body = f"""Redefinição de Senha - Orion P&D

Olá, {user.full_name}!

Acesse o link abaixo para redefinir sua senha:
{reset_url}

Este link é válido por 1 hora.

Se você não solicitou a redefinição, ignore este email.
"""

    if tenant and tenant.email_enabled and tenant.mail_server:
        return send_email_via_tenant(tenant, user.email, subject, html_body, text_body)

    # Fallback: try global Flask-Mail config
    try:
        from flask import current_app
        from flask_mail import Mail, Message
        mail = Mail(current_app)
        msg = Message(subject, recipients=[user.email], html=html_body, body=text_body)
        mail.send(msg)
        return True, None
    except Exception as e:
        logger.error(f"Fallback email failed: {e}")
        return False, str(e)
