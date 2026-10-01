"""
Email service using per-tenant SMTP configuration.
"""
import smtplib
import ssl
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr, parseaddr

logger = logging.getLogger(__name__)

# Version marker included in error messages so stale deployments can be
# detected from the flash message alone
EMAIL_SERVICE_VERSION = '3.0.3'

SMTP_TIMEOUT = 30


class _UTF8AuthMixin:
    """
    smtplib hardcodes ASCII when encoding AUTH credentials, so usernames or
    passwords containing accents raise "'ascii' codec can't encode".
    RFC 4954 SASL PLAIN/LOGIN allow UTF-8; re-implement auth() with it.
    """

    def auth(self, mechanism, authobject, *, initial_response_ok=True):
        import base64
        from smtplib import SMTPAuthenticationError, SMTPException

        mechanism = mechanism.upper()
        initial_response = (authobject() if initial_response_ok else None)
        if initial_response is not None:
            response = base64.b64encode(initial_response.encode('utf-8')).decode('ascii')
            (code, resp) = self.docmd("AUTH", mechanism + " " + response)
            self._auth_challenge_count = 1
        else:
            (code, resp) = self.docmd("AUTH", mechanism)
            self._auth_challenge_count = 0
        while code == 334:
            self._auth_challenge_count += 1
            challenge = base64.decodebytes(resp)
            response = base64.b64encode(authobject(challenge).encode('utf-8')).decode('ascii')
            (code, resp) = self.docmd(response)
            if self._auth_challenge_count > 5:
                raise SMTPException("Server AUTH mechanism infinite loop.")
        if code in (235, 503):
            return (code, resp)
        raise SMTPAuthenticationError(code, resp)


class _SMTP(_UTF8AuthMixin, smtplib.SMTP):
    pass


class _SMTP_SSL(_UTF8AuthMixin, smtplib.SMTP_SSL):
    pass


def _open_smtp(host, port, use_ssl, use_tls):
    """Open an SMTP connection in the given mode (implicit SSL or STARTTLS)."""
    if use_ssl:
        server = _SMTP_SSL(host, port, timeout=SMTP_TIMEOUT)
        server.ehlo()
    else:
        server = _SMTP(host, port, timeout=SMTP_TIMEOUT)
        server.ehlo()
        if use_tls:
            server.starttls()
            server.ehlo()
    return server


def _resolve_security_mode(port, use_ssl, use_tls):
    """
    Normalize the SSL/TLS mode based on the port to avoid the classic
    WRONG_VERSION_NUMBER error caused by mismatched port/security combos:
      - port 465 -> implicit SSL (SMTP_SSL)
      - port 587/25 -> STARTTLS (plain connection upgraded)
    """
    if port == 465:
        return True, False
    if port in (587, 25):
        return False, True if (use_tls or use_ssl) else False
    # Non-standard port: respect what was configured
    return bool(use_ssl), bool(use_tls)


def _build_message(subject, sender, to_email, html_body, text_body=None):
    """Build a MIME message with all headers RFC 2047-safe."""
    sender_name, sender_addr = parseaddr(sender or '')
    if not sender_addr:
        sender_addr = sender or ''

    msg = MIMEMultipart('alternative')
    msg['Subject'] = Header(subject, 'utf-8')
    if sender_name:
        msg['From'] = formataddr((str(Header(sender_name, 'utf-8')), sender_addr))
    else:
        msg['From'] = sender_addr
    msg['To'] = to_email

    if text_body:
        msg.attach(MIMEText(text_body, 'plain', 'utf-8'))
    msg.attach(MIMEText(html_body, 'html', 'utf-8'))
    return msg, sender_addr


def _send_via_smtp(host, port, use_ssl, use_tls, username, password,
                   sender, to_email, subject, html_body, text_body=None,
                   origin='smtp'):
    """
    Single hardened send path. Returns (success: bool, error: str|None).

    The flattened message is encoded to UTF-8 bytes BEFORE handing it to
    smtplib: sendmail() only applies its internal ASCII encoding to str
    payloads, so passing bytes eliminates any possible
    "'ascii' codec can't encode" error regardless of message content.
    """
    msg, sender_addr = _build_message(subject, sender, to_email, html_body, text_body)
    port = port or 587
    use_ssl, use_tls = _resolve_security_mode(port, use_ssl, use_tls)

    # Primary attempt + fallback with the opposite mode if the TLS handshake
    # fails (e.g. WRONG_VERSION_NUMBER when port/security combo is mismatched)
    if use_ssl:
        attempts = [(True, False), (False, True)]     # SSL first, then STARTTLS
    else:
        attempts = [(False, use_tls), (True, False)]  # STARTTLS/plain first, then SSL
    last_error = None

    payload = msg.as_string().encode('utf-8')

    for i, (ssl_mode, tls_mode) in enumerate(attempts):
        try:
            server = _open_smtp(host, port, ssl_mode, tls_mode)
            server.login(username, password)
            server.sendmail(sender_addr, [to_email], payload)
            server.quit()
            mode = 'SSL' if ssl_mode else ('STARTTLS' if tls_mode else 'plain')
            logger.info(f"Email sent to {to_email} via {origin} ({host}:{port} {mode})")
            return True, None
        except (ssl.SSLError, smtplib.SMTPServerDisconnected, ConnectionResetError, OSError) as e:
            last_error = e
            logger.warning(f"SMTP attempt {i+1} failed for {host}:{port} (ssl={ssl_mode}, tls={tls_mode}): {e}")
            continue  # try the alternate security mode
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP auth failed for {username}@{host}: {e}")
            return False, (f"Falha de autenticação SMTP: verifique usuário e senha "
                           f"(para Gmail use Senha de App). Detalhe: {e} "
                           f"[email v{EMAIL_SERVICE_VERSION}]")
        except UnicodeEncodeError as e:
            logger.error(f"Unicode error in SMTP credentials for {host}: {e}")
            return False, (f"A senha ou usuário SMTP contém caracteres especiais/acentos "
                           f"não suportados pelo servidor de email. Use uma senha sem acentos. "
                           f"[email v{EMAIL_SERVICE_VERSION}]")
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False, f"{e} [email v{EMAIL_SERVICE_VERSION}]"

    hint = ""
    if isinstance(last_error, ssl.SSLError):
        hint = (" Verifique a combinação porta/segurança na configuração da empresa: "
                "porta 465 = SSL, porta 587 = TLS.")
    logger.error(f"Failed to send email to {to_email} after retries: {last_error}")
    return False, f"{last_error}.{hint} [email v{EMAIL_SERVICE_VERSION}]"


def send_email_via_tenant(tenant, to_email, subject, html_body, text_body=None):
    """
    Send an email using the tenant's SMTP configuration.
    Returns (success: bool, error_message: str|None).
    """
    if not tenant or not tenant.email_enabled:
        return False, "Email not enabled for this tenant"

    if not tenant.mail_server or not tenant.mail_username or not tenant.mail_password:
        return False, "Incomplete SMTP configuration"

    return _send_via_smtp(
        host=tenant.mail_server,
        port=tenant.mail_port,
        use_ssl=tenant.mail_use_ssl,
        use_tls=tenant.mail_use_tls,
        username=tenant.mail_username,
        password=tenant.mail_password,
        sender=tenant.mail_default_sender or tenant.mail_username,
        to_email=to_email,
        subject=subject,
        html_body=html_body,
        text_body=text_body,
        origin=f'tenant {tenant.name}',
    )


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

    # Fallback: global SMTP settings (MAIL_* environment variables) using the
    # same hardened send path (no Flask-Mail, which has its own encoding quirks)
    try:
        from flask import current_app
        cfg = current_app.config
        if not cfg.get('MAIL_SERVER') or not cfg.get('MAIL_USERNAME'):
            return False, ("Nenhum SMTP configurado: habilite o email da empresa "
                           "(Empresas > Editar > Configuração de Email) ou defina as "
                           f"variáveis MAIL_* no servidor. [email v{EMAIL_SERVICE_VERSION}]")
        return _send_via_smtp(
            host=cfg.get('MAIL_SERVER'),
            port=cfg.get('MAIL_PORT'),
            use_ssl=cfg.get('MAIL_USE_SSL', False),
            use_tls=cfg.get('MAIL_USE_TLS', True),
            username=cfg.get('MAIL_USERNAME'),
            password=cfg.get('MAIL_PASSWORD'),
            sender=cfg.get('MAIL_DEFAULT_SENDER') or cfg.get('MAIL_USERNAME'),
            to_email=user.email,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
            origin='global config',
        )
    except Exception as e:
        logger.error(f"Fallback email failed: {e}")
        return False, f"{e} [email v{EMAIL_SERVICE_VERSION}]"
