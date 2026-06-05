import os
import sys
import logging
from flask import Flask, redirect, url_for, g
from flask_login import LoginManager, current_user
from flask_mail import Mail

# Add project directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import db, User, Tenant

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Global mail instance
mail = Mail()

def create_app():
    app = Flask(__name__)

    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'chave-secreta-pd-gestao-2024-alterar-em-producao')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///rd_projects.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # File upload configuration
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max file size
    app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'}

    # Email configuration (Flask-Mail)
    app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True').lower() in ('true', '1', 'yes')
    app.config['MAIL_USE_SSL'] = os.environ.get('MAIL_USE_SSL', 'False').lower() in ('true', '1', 'yes')
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', '')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'Orion PMO <noreply@orionpmo.com>')

    # Ensure upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    mail.init_app(app)

    # Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Por favor, faça login para acessar esta página.'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

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
    from routes.ai import ai_bp
    from routes.home import home_bp
    from routes.status_report import status_report_bp
    from routes.meeting_minutes import meeting_minutes_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(expenses_bp)
    app.register_blueprint(resources_bp)
    app.register_blueprint(schedule_bp)
    app.register_blueprint(timesheet_bp)
    app.register_blueprint(public_calls_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(tenants_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(home_bp)
    app.register_blueprint(status_report_bp)
    app.register_blueprint(meeting_minutes_bp)

    # Optional audit blueprint
    has_audit = False
    try:
        from routes.audit import audit_bp
        app.register_blueprint(audit_bp)
        has_audit = True
    except ImportError as e:
        logging.warning(f"Audit module not loaded: {e}")

    # Optional blueprints (Programs and Portfolio modules)
    has_programs = False
    has_portfolio = False

    try:
        from routes.programs import programs_bp
        app.register_blueprint(programs_bp)
        has_programs = True
    except ImportError:
        pass

    try:
        from routes.portfolio import portfolio_bp
        app.register_blueprint(portfolio_bp)
        has_portfolio = True
    except ImportError:
        pass

    # Optional Agile blueprint
    has_agile = False
    try:
        from routes.agile import agile_bp
        app.register_blueprint(agile_bp)
        has_agile = True
    except ImportError:
        pass

    # Optional Compliance blueprint
    has_compliance = False
    try:
        from routes.compliance import compliance_bp
        app.register_blueprint(compliance_bp)
        has_compliance = True
    except ImportError:
        pass

    # Optional PMO Agents blueprint (Orion Autônomos PMO)
    has_pmo_agents = False
    try:
        from routes.pmo_agents import pmo_agents_bp
        app.register_blueprint(pmo_agents_bp)
        has_pmo_agents = True
    except ImportError as e:
        logging.warning(f"PMO Agents module not loaded: {e}")

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
            'is_superadmin': current_user.is_superadmin() if current_user.is_authenticated else False,
            'has_programs_module': has_programs,
            'has_portfolio_module': has_portfolio,
            'has_audit_module': has_audit,
            'has_agile_module': has_agile,
            'has_compliance_module': has_compliance,
            'has_pmo_agents_module': has_pmo_agents
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
