import secrets
from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from flask_babel import refresh
from models import db, User, AuditLog
from extensions import LANGUAGES

auth_bp = Blueprint('auth', __name__)


def get_portal_news():
    """Get news for the login portal."""
    try:
        from services.news_scraper import get_innovation_news
        return get_innovation_news(finep_limit=3, fapesc_limit=3)
    except Exception:
        return []


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home.dashboard'))

    news = get_portal_news()

    if request.method == 'POST':
        login_input = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        user = User.query.filter(
            db.or_(
                User.email == login_input,
                User.username == login_input
            )
        ).first()

        if user and user.active and user.check_password(password):
            if user.tenant_id and user.tenant:
                if not user.tenant.is_active():
                    flash('Sua empresa está com a licença expirada ou inativa. Entre em contato com o suporte.', 'danger')
                    return render_template('auth/login.html', news=news)

            login_user(user)

            # Log login
            try:
                AuditLog.log(action='login', entity_type='user', entity_id=user.id, entity_name=user.full_name)
                db.session.commit()
            except Exception:
                pass

            next_page = request.args.get('next')
            flash('Login realizado com sucesso!', 'success')
            return redirect(next_page or url_for('home.dashboard'))
        elif user and not user.active:
            flash('Sua conta está desativada. Entre em contato com o administrador.', 'danger')
        else:
            flash('Email/usuário ou senha incorretos.', 'danger')

    return render_template('auth/login.html', news=news)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('projects.list_projects'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        full_name = request.form.get('full_name', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not all([username, email, full_name, password]):
            flash('Todos os campos são obrigatórios.', 'danger')
            return render_template('auth/register.html')

        if password != confirm_password:
            flash('As senhas não coincidem.', 'danger')
            return render_template('auth/register.html')

        if len(password) < 6:
            flash('A senha deve ter pelo menos 6 caracteres.', 'danger')
            return render_template('auth/register.html')

        if User.query.filter_by(username=username).first():
            flash('Nome de usuário já existe.', 'danger')
            return render_template('auth/register.html')

        if User.query.filter_by(email=email).first():
            flash('Email já cadastrado.', 'danger')
            return render_template('auth/register.html')

        user = User(username=username, email=email, full_name=full_name)
        user.set_password(password)

        # First user becomes admin
        if User.query.count() == 0:
            user.role = 'admin'

        db.session.add(user)
        db.session.commit()

        flash('Cadastro realizado com sucesso! Faça login.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')


@auth_bp.route('/logout')
@login_required
def logout():
    # Log logout before clearing session
    try:
        AuditLog.log(action='logout', entity_type='user', entity_id=current_user.id, entity_name=current_user.full_name)
        db.session.commit()
    except Exception:
        pass

    logout_user()
    flash('Logout realizado com sucesso.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('home.dashboard'))

    if request.method == 'POST':
        email_input = request.form.get('email', '').strip()
        user = User.query.filter_by(email=email_input, active=True).first()

        if user:
            token = secrets.token_urlsafe(32)
            user.password_reset_token = token
            user.password_reset_expires = datetime.utcnow() + timedelta(hours=1)
            db.session.commit()

            reset_url = url_for('auth.reset_password', token=token, _external=True)
            from services.email_service import send_password_reset_email
            success, error = send_password_reset_email(user, reset_url)
            if not success:
                flash(f'Erro ao enviar email: {error}. Contate o administrador.', 'warning')
            else:
                flash('Se este email estiver cadastrado, você receberá um link para redefinir sua senha.', 'info')
        else:
            # Always show the same message to prevent email enumeration
            flash('Se este email estiver cadastrado, você receberá um link para redefinir sua senha.', 'info')

        return redirect(url_for('auth.login'))

    return render_template('auth/forgot_password.html')


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('home.dashboard'))

    user = User.query.filter_by(password_reset_token=token, active=True).first()
    if not user or not user.password_reset_expires or user.password_reset_expires < datetime.utcnow():
        flash('Link de redefinição inválido ou expirado. Solicite um novo.', 'danger')
        return redirect(url_for('auth.forgot_password'))

    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')

        if len(password) < 6:
            flash('A senha deve ter pelo menos 6 caracteres.', 'danger')
            return render_template('auth/reset_password.html', token=token)

        if password != confirm:
            flash('As senhas não coincidem.', 'danger')
            return render_template('auth/reset_password.html', token=token)

        user.set_password(password)
        user.password_reset_token = None
        user.password_reset_expires = None
        db.session.commit()

        flash('Senha redefinida com sucesso! Faça login com sua nova senha.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/reset_password.html', token=token)


@auth_bp.route('/set-language/<lang>')
def set_language(lang):
    """Set user language preference."""
    # Normalize language code
    lang = lang.replace('-', '_')

    if lang not in LANGUAGES:
        lang = 'pt_BR'

    if current_user.is_authenticated:
        current_user.language = lang
        db.session.commit()

    # Also store in session for anonymous users
    session['language'] = lang

    # Refresh babel to use new language
    refresh()

    # Redirect back to previous page
    referrer = request.referrer
    if referrer and 'login' not in referrer:
        return redirect(referrer)
    return redirect(url_for('home.dashboard') if current_user.is_authenticated else url_for('auth.login'))
