from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('projects.list_projects'))

    if request.method == 'POST':
        login_input = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        # Try to find user by email or username
        user = User.query.filter(
            db.or_(
                User.email == login_input,
                User.username == login_input
            )
        ).first()

        if user and user.active and user.check_password(password):
            # Check if tenant is active (for non-superadmin users)
            if user.tenant_id and user.tenant:
                if not user.tenant.is_active():
                    flash('Sua empresa está com a licença expirada ou inativa. Entre em contato com o suporte.', 'danger')
                    return render_template('auth/login.html')

            login_user(user)
            next_page = request.args.get('next')
            flash('Login realizado com sucesso!', 'success')
            return redirect(next_page or url_for('projects.list_projects'))
        elif user and not user.active:
            flash('Sua conta está desativada. Entre em contato com o administrador.', 'danger')
        else:
            flash('Email/usuário ou senha incorretos.', 'danger')

    return render_template('auth/login.html')


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
    logout_user()
    flash('Logout realizado com sucesso.', 'info')
    return redirect(url_for('auth.login'))
