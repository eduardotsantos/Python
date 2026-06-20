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
