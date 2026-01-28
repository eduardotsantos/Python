import os
import sys
import logging
from flask import Flask, redirect, url_for
from flask_login import LoginManager

# Add project directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import db, User

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

    app.register_blueprint(auth_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(expenses_bp)
    app.register_blueprint(resources_bp)
    app.register_blueprint(schedule_bp)
    app.register_blueprint(timesheet_bp)
    app.register_blueprint(public_calls_bp)

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

        # Create default admin if no users exist
        if User.query.count() == 0:
            admin = User(
                username='admin',
                email='admin@gestaopdp.com',
                full_name='Administrador',
                role='admin'
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            logging.info("Default admin user created: admin / admin123")

    return app


if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
