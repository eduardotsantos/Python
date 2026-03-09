import os
import sys
import logging
from flask import Flask, redirect, url_for, g
from flask_login import LoginManager, current_user

# Add project directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import db, User, Tenant

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def create_app():
    app = Flask(__name__)

    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'chave-secreta-pd-gestao-2024-alterar-em-producao')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///rd_projects.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize extensions
    db.init_app(app)

    # Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Por favor, faça login para acessar esta página.'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    from routes.auth import auth_bp
    from routes.projects import projects_bp
    from routes.expenses import expenses_bp
    from routes.resources import resources_bp
    from routes.schedule import schedule_bp
    from routes.timesheet import timesheet_bp
    from routes.public_calls import public_calls_bp
    from routes.users import users_bp
    from routes.tenants import tenants_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(expenses_bp)
    app.register_blueprint(resources_bp)
    app.register_blueprint(schedule_bp)
    app.register_blueprint(timesheet_bp)
    app.register_blueprint(public_calls_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(tenants_bp)

    # Before request - set current tenant
    @app.before_request
    def set_tenant_context():
        g.current_tenant = None
        if current_user.is_authenticated and current_user.tenant_id:
            g.current_tenant = current_user.tenant

    # Context processor to make tenant available in templates
    @app.context_processor
    def inject_tenant():
        return {
            'current_tenant': getattr(g, 'current_tenant', None),
            'is_superadmin': current_user.is_superadmin() if current_user.is_authenticated else False
        }

    # Root redirect
    @app.route('/')
    def index():
        return redirect(url_for('auth.login'))

    # Jinja2 filters
    @app.template_filter('currency_brl')
    def currency_brl(value):
        try:
            return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except (ValueError, TypeError):
            return "R$ 0,00"

    # Create tables
    with app.app_context():
        db.create_all()

        # Create default super admin if no superadmin exists
        superadmin = User.query.filter_by(role='superadmin').first()
        if not superadmin:
            superadmin = User(
                tenant_id=None,  # Super admin has no tenant
                username='superadmin',
                email='superadmin@gestaopdp.com',
                full_name='Super Administrador',
                role='superadmin'
            )
            superadmin.set_password('super123')
            db.session.add(superadmin)
            db.session.commit()
            logging.info("Default super admin user created: superadmin / super123")

    return app


if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
