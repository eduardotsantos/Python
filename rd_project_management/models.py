from datetime import datetime, date
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), default='user')  # admin, manager, user
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    active = db.Column(db.Boolean, default=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Project(db.Model):
    __tablename__ = 'projects'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(50), default='Planejamento')  # Planejamento, Em Andamento, Concluído, Cancelado
    category = db.Column(db.String(100))  # Inovação, Pesquisa Básica, Desenvolvimento Experimental
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    budget = db.Column(db.Float, default=0.0)
    funding_source = db.Column(db.String(200))  # FINEP, BNDES, Próprio, etc.
    responsible_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    responsible = db.relationship('User', backref='projects')
    expenses = db.relationship('Expense', backref='project', cascade='all, delete-orphan')
    resources = db.relationship('Resource', backref='project', cascade='all, delete-orphan')
    milestones = db.relationship('Milestone', backref='project', cascade='all, delete-orphan')
    timesheets = db.relationship('Timesheet', backref='project', cascade='all, delete-orphan')


class Expense(db.Model):
    __tablename__ = 'expenses'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    description = db.Column(db.String(300), nullable=False)
    category = db.Column(db.String(100), nullable=False)  # Pessoal, Equipamento, Material, Viagem, Serviço Terceiro, Outros
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    receipt_number = db.Column(db.String(100))
    supplier = db.Column(db.String(200))
    status = db.Column(db.String(50), default='Pendente')  # Pendente, Aprovada, Rejeitada, Paga
    notes = db.Column(db.Text)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    created_by = db.relationship('User', backref='expenses')


class Resource(db.Model):
    __tablename__ = 'resources'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # Pessoa, Máquina
    name = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(100))  # Pesquisador, Técnico, Bolsista, etc.
    hours_allocated = db.Column(db.Float, default=0.0)
    hourly_cost = db.Column(db.Float, default=0.0)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    status = db.Column(db.String(50), default='Ativo')  # Ativo, Inativo
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Milestone(db.Model):
    __tablename__ = 'milestones'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    progress = db.Column(db.Integer, default=0)  # 0-100%
    status = db.Column(db.String(50), default='Pendente')  # Pendente, Em Andamento, Concluído, Atrasado
    order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Timesheet(db.Model):
    __tablename__ = 'timesheets'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    resource_id = db.Column(db.Integer, db.ForeignKey('resources.id'), nullable=True)
    date = db.Column(db.Date, nullable=False)
    hours = db.Column(db.Float, nullable=False)
    activity = db.Column(db.String(300), nullable=False)
    milestone_id = db.Column(db.Integer, db.ForeignKey('milestones.id'), nullable=True)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='timesheets')
    milestone = db.relationship('Milestone', backref='timesheets')
    resource = db.relationship('Resource', backref='timesheets')


class PublicCall(db.Model):
    __tablename__ = 'public_calls'
    id = db.Column(db.Integer, primary_key=True)
    source = db.Column(db.String(50), nullable=False)  # FINEP, BNDES, Outro
    title = db.Column(db.String(500), nullable=False)
    theme = db.Column(db.String(300))
    description = db.Column(db.Text)
    publication_date = db.Column(db.String(100))
    deadline = db.Column(db.String(100))
    funding_source = db.Column(db.String(200))
    target_audience = db.Column(db.String(300))
    url = db.Column(db.String(500))
    status = db.Column(db.String(50), default='Aberta')  # Aberta, Encerrada, Em Análise
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('source', 'title', 'url', name='uq_public_call'),
    )

    # Relationship to project links
    project_links = db.relationship('ProjectCall', backref='public_call', cascade='all, delete-orphan')


class ProjectCall(db.Model):
    """Links between public calls and projects (when a project is linked to a funding call)."""
    __tablename__ = 'project_calls'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    public_call_id = db.Column(db.Integer, db.ForeignKey('public_calls.id'), nullable=False)
    linked_at = db.Column(db.Date, nullable=False, default=date.today)
    notes = db.Column(db.Text)
    status = db.Column(db.String(50), default='Vinculado')  # Vinculado, Submetido, Aprovado, Rejeitado
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    project = db.relationship('Project', backref='call_links')
