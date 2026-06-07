from datetime import datetime, date
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class Tenant(db.Model):
    """Tenant model for multi-tenancy support."""
    __tablename__ = 'tenants'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)  # URL-friendly identifier
    cnpj = db.Column(db.String(20))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    state = db.Column(db.String(2))  # UF - sigla do estado
    municipality = db.Column(db.String(200))  # Município
    logo_url = db.Column(db.String(500))
    plan = db.Column(db.String(50), default='basic')  # basic, professional, enterprise
    max_users = db.Column(db.Integer, default=5)
    max_projects = db.Column(db.Integer, default=10)
    active = db.Column(db.Boolean, default=True)
    expires_at = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Email configuration per tenant
    email_enabled = db.Column(db.Boolean, default=False)  # Enable/disable email sending
    mail_server = db.Column(db.String(200))  # SMTP server (e.g., smtp.gmail.com)
    mail_port = db.Column(db.Integer, default=587)
    mail_use_tls = db.Column(db.Boolean, default=True)
    mail_use_ssl = db.Column(db.Boolean, default=False)
    mail_username = db.Column(db.String(200))  # SMTP username/email
    mail_password = db.Column(db.String(200))  # SMTP password (encrypted in production)
    mail_default_sender = db.Column(db.String(200))  # Default sender name and email

    # Relationships
    users = db.relationship('User', backref='tenant', lazy='dynamic')
    projects = db.relationship('Project', backref='tenant', lazy='dynamic')
    public_calls = db.relationship('PublicCall', backref='tenant', lazy='dynamic')

    def is_active(self):
        """Check if tenant subscription is active."""
        if not self.active:
            return False
        if self.expires_at and self.expires_at < date.today():
            return False
        return True

    def can_add_user(self):
        """Check if tenant can add more users."""
        return self.users.count() < self.max_users

    def can_add_project(self):
        """Check if tenant can add more projects."""
        return self.projects.count() < self.max_projects

    def can_generate_proposals(self):
        """Check if tenant plan allows AI proposal generation."""
        return self.plan in ('professional', 'enterprise')


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=True)  # Null for super admin
    username = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), default='user')  # superadmin, admin, manager, user, viewer
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    active = db.Column(db.Boolean, default=True)

    # Email notification preferences
    email_notifications = db.Column(db.Boolean, default=True)  # Receive email notifications
    email_briefing_daily = db.Column(db.Boolean, default=True)  # Receive daily briefing
    email_alerts = db.Column(db.Boolean, default=True)  # Receive critical alerts

    __table_args__ = (
        db.UniqueConstraint('tenant_id', 'username', name='uq_tenant_username'),
        db.UniqueConstraint('tenant_id', 'email', name='uq_tenant_email'),
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_superadmin(self):
        return self.role == 'superadmin' and self.tenant_id is None

    def is_tenant_admin(self):
        return self.role == 'admin'

    def is_viewer(self):
        return self.role == 'viewer'

    def can_edit(self):
        """Check if user can edit/create content."""
        return self.role in ['superadmin', 'admin', 'manager', 'user']


class Project(db.Model):
    __tablename__ = 'projects'
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
    program_id = db.Column(db.Integer, db.ForeignKey('programs.id'), nullable=True)
    code = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(50), default='Planejamento')
    category = db.Column(db.String(100))
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    budget = db.Column(db.Float, default=0.0)
    funding_source = db.Column(db.String(200))
    responsible_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # PMBOK 8 - Value Delivery fields
    expected_value = db.Column(db.Float, default=0.0)
    value_type = db.Column(db.String(50))  # ROI, Economia, Receita, Estratégico
    value_status = db.Column(db.String(50), default='Não iniciado')  # Não iniciado, Em captura, Parcial, Realizado
    realized_value = db.Column(db.Float, default=0.0)

    __table_args__ = (
        db.UniqueConstraint('tenant_id', 'code', name='uq_tenant_project_code'),
    )

    responsible = db.relationship('User', backref='projects')
    expenses = db.relationship('Expense', backref='project', cascade='all, delete-orphan')
    resources = db.relationship('Resource', backref='project', cascade='all, delete-orphan')
    milestones = db.relationship('Milestone', backref='project', cascade='all, delete-orphan')
    timesheets = db.relationship('Timesheet', backref='project', cascade='all, delete-orphan')
    documents = db.relationship('ProjectDocument', backref='project', cascade='all, delete-orphan')


class Expense(db.Model):
    __tablename__ = 'expenses'
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    description = db.Column(db.String(300), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    receipt_number = db.Column(db.String(100))
    supplier = db.Column(db.String(200))
    status = db.Column(db.String(50), default='Pendente')
    notes = db.Column(db.Text)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    created_by = db.relationship('User', backref='expenses')
    attachments = db.relationship('ExpenseAttachment', backref='expense', cascade='all, delete-orphan')


class ExpenseAttachment(db.Model):
    """Attachments for expenses (boletos, notas fiscais, comprovantes)."""
    __tablename__ = 'expense_attachments'
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
    expense_id = db.Column(db.Integer, db.ForeignKey('expenses.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(50), nullable=False)
    file_size = db.Column(db.Integer)
    attachment_type = db.Column(db.String(50), nullable=False)  # boleto, nota_fiscal, comprovante
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    uploaded_by = db.relationship('User', backref='expense_attachments')

    @property
    def file_size_display(self):
        """Return human-readable file size."""
        if not self.file_size:
            return "0 B"
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    @property
    def attachment_type_display(self):
        """Return human-readable attachment type."""
        types = {
            'boleto': 'Boleto',
            'nota_fiscal': 'Nota Fiscal',
            'comprovante': 'Comprovante de Pagamento'
        }
        return types.get(self.attachment_type, self.attachment_type)


class Resource(db.Model):
    __tablename__ = 'resources'
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(100))
    hours_allocated = db.Column(db.Float, default=0.0)
    hourly_cost = db.Column(db.Float, default=0.0)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    status = db.Column(db.String(50), default='Ativo')
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Sprint(db.Model):
    """Sprint for agile project management."""
    __tablename__ = 'sprints'
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    number = db.Column(db.Integer, default=1)
    goal = db.Column(db.Text)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(50), default='Planejado')  # Planejado, Ativo, Concluído
    velocity = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    milestones = db.relationship('Milestone', backref='sprint', lazy='dynamic')


class MilestoneResource(db.Model):
    """Association table linking milestones to resources with allocation percentage."""
    __tablename__ = 'milestone_resources'
    id = db.Column(db.Integer, primary_key=True)
    milestone_id = db.Column(db.Integer, db.ForeignKey('milestones.id'), nullable=False)
    resource_id = db.Column(db.Integer, db.ForeignKey('resources.id'), nullable=False)
    allocation = db.Column(db.Integer, default=100)  # % de alocação (0-100)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    milestone = db.relationship('Milestone', backref=db.backref('resource_assignments', cascade='all, delete-orphan'))
    resource = db.relationship('Resource', backref='milestone_assignments')

    __table_args__ = (
        db.UniqueConstraint('milestone_id', 'resource_id', name='uq_milestone_resource'),
    )


class Milestone(db.Model):
    __tablename__ = 'milestones'
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    sprint_id = db.Column(db.Integer, db.ForeignKey('sprints.id'), nullable=True)
    predecessor_id = db.Column(db.Integer, db.ForeignKey('milestones.id'), nullable=True)
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    progress = db.Column(db.Integer, default=0)
    status = db.Column(db.String(50), default='Pendente')
    priority = db.Column(db.String(20), default='Média')  # Baixa, Média, Alta, Crítica
    story_points = db.Column(db.Integer, default=0)
    order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    predecessor = db.relationship('Milestone', remote_side=[id], backref='successors', foreign_keys=[predecessor_id])

    @property
    def responsibles(self):
        """Return list of responsible resources with allocation."""
        return [(ra.resource, ra.allocation) for ra in self.resource_assignments]

    @property
    def responsible_names(self):
        """Return comma-separated list of responsible names."""
        return ', '.join([ra.resource.name for ra in self.resource_assignments])


class Timesheet(db.Model):
    __tablename__ = 'timesheets'
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
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
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=True)  # Null = global/shared
    source = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(500), nullable=False)
    theme = db.Column(db.String(300))
    description = db.Column(db.Text)
    publication_date = db.Column(db.String(100))
    deadline = db.Column(db.String(100))
    funding_source = db.Column(db.String(200))
    target_audience = db.Column(db.String(300))
    url = db.Column(db.String(500))
    status = db.Column(db.String(50), default='Aberta')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('source', 'title', 'url', name='uq_public_call'),
    )

    project_links = db.relationship('ProjectCall', backref='public_call', cascade='all, delete-orphan')


class ProjectCall(db.Model):
    """Links between public calls and projects."""
    __tablename__ = 'project_calls'
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    public_call_id = db.Column(db.Integer, db.ForeignKey('public_calls.id'), nullable=False)
    linked_at = db.Column(db.Date, nullable=False, default=date.today)
    notes = db.Column(db.Text)
    status = db.Column(db.String(50), default='Vinculado')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    project = db.relationship('Project', backref='call_links')


class ProjectDocument(db.Model):
    """Documents attached to projects (PDF, Word, Excel, PowerPoint)."""
    __tablename__ = 'project_documents'
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)  # Original filename
    stored_filename = db.Column(db.String(255), nullable=False)  # UUID filename on disk
    file_type = db.Column(db.String(50), nullable=False)  # pdf, docx, xlsx, pptx
    file_size = db.Column(db.Integer)  # Size in bytes
    description = db.Column(db.String(300))
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    uploaded_by = db.relationship('User', backref='uploaded_documents')

    @property
    def uploaded_at(self):
        """Alias for created_at for template compatibility."""
        return self.created_at

    @property
    def file_size_display(self):
        """Return human-readable file size."""
        if not self.file_size:
            return "0 B"
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    @property
    def file_icon(self):
        """Return Bootstrap icon class based on file type."""
        icons = {
            'pdf': 'bi-file-earmark-pdf text-danger',
            'doc': 'bi-file-earmark-word text-primary',
            'docx': 'bi-file-earmark-word text-primary',
            'xls': 'bi-file-earmark-excel text-success',
            'xlsx': 'bi-file-earmark-excel text-success',
            'ppt': 'bi-file-earmark-ppt text-warning',
            'pptx': 'bi-file-earmark-ppt text-warning',
        }
        return icons.get(self.file_type, 'bi-file-earmark')


class AuditLog(db.Model):
    """Audit log for tracking user actions."""
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(50), nullable=False)  # login, logout, create, update, delete
    entity_type = db.Column(db.String(100))  # project, expense, user, etc.
    entity_id = db.Column(db.Integer)
    entity_name = db.Column(db.String(300))  # Human-readable name
    details = db.Column(db.Text)  # JSON with changed fields
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='audit_logs')
    tenant = db.relationship('Tenant', backref='audit_logs')

    @staticmethod
    def log(action, entity_type=None, entity_id=None, entity_name=None, details=None):
        """Create an audit log entry."""
        from flask_login import current_user
        from flask import request

        log_entry = AuditLog(
            tenant_id=current_user.tenant_id if current_user.is_authenticated else None,
            user_id=current_user.id if current_user.is_authenticated else None,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            details=details,
            ip_address=request.remote_addr if request else None,
            user_agent=request.user_agent.string[:500] if request and request.user_agent else None
        )
        db.session.add(log_entry)
        return log_entry


class Program(db.Model):
    """Program model - groups related projects."""
    __tablename__ = 'programs'
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
    code = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text)
    objective = db.Column(db.Text)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    budget = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(50), default='Ativo')
    manager_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('tenant_id', 'code', name='uq_tenant_program_code'),
    )

    manager = db.relationship('User', backref='managed_programs')
    tenant = db.relationship('Tenant', backref='programs')
    projects = db.relationship('Project', backref='program', lazy='dynamic')

    @property
    def total_budget(self):
        """Sum of all project budgets."""
        return sum(p.budget or 0 for p in self.projects)

    @property
    def total_spent(self):
        """Sum of all project expenses."""
        from sqlalchemy import func
        return db.session.query(func.sum(Expense.amount)).filter(
            Expense.project_id.in_([p.id for p in self.projects])
        ).scalar() or 0

    @property
    def project_count(self):
        """Number of projects in this program."""
        return self.projects.count()


class SyncSchedule(db.Model):
    """Schedule for automatic sync of public calls."""
    __tablename__ = 'sync_schedules'
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=True)
    source = db.Column(db.String(50), nullable=False)  # fapesc, finep, cnpq, etc.
    frequency = db.Column(db.String(20), default='weekly')  # daily, weekly, monthly
    day_of_week = db.Column(db.Integer, default=0)  # 0=Monday, 6=Sunday
    hour = db.Column(db.Integer, default=8)  # Hour to run (0-23)
    last_run = db.Column(db.DateTime)
    next_run = db.Column(db.DateTime)
    enabled = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tenant = db.relationship('Tenant', backref='sync_schedules')


class MeetingMinutes(db.Model):
    """Meeting minutes for projects."""
    __tablename__ = 'meeting_minutes'
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    title = db.Column(db.String(300), nullable=False)
    meeting_date = db.Column(db.Date, nullable=False)
    meeting_time = db.Column(db.String(10))
    location = db.Column(db.String(200))
    participants = db.Column(db.Text)
    transcription = db.Column(db.Text)
    generated_minutes = db.Column(db.Text)
    status = db.Column(db.String(50), default='Rascunho')
    attachment_filename = db.Column(db.String(255))
    attachment_stored = db.Column(db.String(255))
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    created_by = db.relationship('User', backref='meeting_minutes')
    project = db.relationship('Project', backref='meeting_minutes')


# ============================================================================
# CENTRAL DE PENDÊNCIAS E CONFORMIDADE
# ============================================================================

class Risk(db.Model):
    """Project risks registry."""
    __tablename__ = 'risks'
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=True)
    code = db.Column(db.String(50))  # RSK-2024-001
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(100))  # Técnico, Financeiro, Cronograma, Recursos, Externo
    probability = db.Column(db.Integer, default=3)  # 1-5 scale
    impact = db.Column(db.Integer, default=3)  # 1-5 scale
    response_strategy = db.Column(db.String(50))  # Evitar, Mitigar, Transferir, Aceitar
    status = db.Column(db.String(50), default='Identificado')  # Identificado, Analisado, Em Tratamento, Mitigado, Fechado
    mitigation_plan = db.Column(db.Text)
    contingency_plan = db.Column(db.Text)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    identified_date = db.Column(db.Date, default=date.today)
    review_date = db.Column(db.Date)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = db.relationship('Project', backref='risks')
    owner = db.relationship('User', foreign_keys=[owner_id], backref='owned_risks')
    created_by = db.relationship('User', foreign_keys=[created_by_id], backref='created_risks')

    @property
    def risk_score(self):
        """Calculate risk score based on probability and impact."""
        return (self.probability or 1) * (self.impact or 1)

    @property
    def risk_level(self):
        """Get risk level based on score."""
        score = self.risk_score
        if score >= 16:
            return 'Crítico'
        elif score >= 9:
            return 'Alto'
        elif score >= 4:
            return 'Médio'
        return 'Baixo'


class PendingItem(db.Model):
    """Pending items for projects."""
    __tablename__ = 'pending_items'
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=True)
    code = db.Column(db.String(50))  # PND-2024-001
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(100))  # Documento, Reunião, Aprovação, Contratação, Outro
    priority = db.Column(db.String(20), default='Média')  # Baixa, Média, Alta, Crítica
    status = db.Column(db.String(50), default='Aberta')  # Aberta, Em Andamento, Resolvida, Cancelada
    due_date = db.Column(db.Date)
    resolution_date = db.Column(db.Date)
    responsible_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    resolved_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    resolution_notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = db.relationship('Project', backref='pending_items')
    responsible = db.relationship('User', foreign_keys=[responsible_id], backref='pending_items_responsible')
    created_by = db.relationship('User', foreign_keys=[created_by_id], backref='created_pending_items')
    resolved_by = db.relationship('User', foreign_keys=[resolved_by_id], backref='resolved_pending_items')

    @property
    def is_overdue(self):
        """Check if item is overdue."""
        if self.due_date and self.status in ['Aberta', 'Em Andamento']:
            return self.due_date < date.today()
        return False


class NonConformity(db.Model):
    """Non-conformity records for projects."""
    __tablename__ = 'non_conformities'
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=True)
    code = db.Column(db.String(50))  # NC-2024-001
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text)
    nc_type = db.Column(db.String(100))  # Processo, Produto, Documentação, Auditoria, Cliente, Regulatório
    impact = db.Column(db.String(20))  # Baixo, Médio, Alto
    root_cause = db.Column(db.Text)
    corrective_plan = db.Column(db.Text)
    evidence = db.Column(db.Text)
    status = db.Column(db.String(50), default='Aberta')  # Aberta, Em Análise, Em Tratamento, Verificação, Fechada
    responsible_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    identified_date = db.Column(db.Date, default=date.today)
    due_date = db.Column(db.Date)
    closure_date = db.Column(db.Date)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = db.relationship('Project', backref='non_conformities')
    responsible = db.relationship('User', foreign_keys=[responsible_id], backref='nc_responsible')
    created_by = db.relationship('User', foreign_keys=[created_by_id], backref='created_non_conformities')


class Bug(db.Model):
    """Bug tracking for software projects."""
    __tablename__ = 'bugs'
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=True)
    code = db.Column(db.String(50))  # BUG-2024-001
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text)
    severity = db.Column(db.String(20))  # Baixa, Média, Alta, Crítica
    environment = db.Column(db.String(100))  # Desenvolvimento, Homologação, Produção
    steps_to_reproduce = db.Column(db.Text)
    expected_behavior = db.Column(db.Text)
    actual_behavior = db.Column(db.Text)
    evidence = db.Column(db.Text)  # Screenshots, logs, etc.
    status = db.Column(db.String(50), default='Aberto')  # Aberto, Em Análise, Em Correção, Teste, Resolvido, Fechado
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    reported_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    reported_date = db.Column(db.Date, default=date.today)
    resolved_date = db.Column(db.Date)
    resolution_notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = db.relationship('Project', backref='bugs')
    assigned_to = db.relationship('User', foreign_keys=[assigned_to_id], backref='assigned_bugs')
    reported_by = db.relationship('User', foreign_keys=[reported_by_id], backref='reported_bugs')


class CorrectiveAction(db.Model):
    """Corrective actions linked to pending items, bugs, non-conformities, or risks."""
    __tablename__ = 'corrective_actions'
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=True)
    code = db.Column(db.String(50))  # AC-2024-001
    description = db.Column(db.Text, nullable=False)
    action_type = db.Column(db.String(50), default='Corretiva')  # Corretiva, Preventiva, Melhoria

    # Links to related items (only one should be filled)
    pending_item_id = db.Column(db.Integer, db.ForeignKey('pending_items.id'), nullable=True)
    non_conformity_id = db.Column(db.Integer, db.ForeignKey('non_conformities.id'), nullable=True)
    bug_id = db.Column(db.Integer, db.ForeignKey('bugs.id'), nullable=True)
    risk_id = db.Column(db.Integer, db.ForeignKey('risks.id'), nullable=True)

    status = db.Column(db.String(50), default='Planejada')  # Planejada, Em Andamento, Concluída, Verificada, Cancelada
    effectiveness = db.Column(db.String(50))  # Eficaz, Parcialmente Eficaz, Não Eficaz
    responsible_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    due_date = db.Column(db.Date)
    completion_date = db.Column(db.Date)
    verification_notes = db.Column(db.Text)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = db.relationship('Project', backref='corrective_actions')
    responsible = db.relationship('User', foreign_keys=[responsible_id], backref='action_responsible')
    pending_item = db.relationship('PendingItem', backref='corrective_actions')
    non_conformity = db.relationship('NonConformity', backref='corrective_actions')
    bug = db.relationship('Bug', backref='corrective_actions')
    risk = db.relationship('Risk', backref='corrective_actions')
    created_by = db.relationship('User', foreign_keys=[created_by_id], backref='created_corrective_actions')

    @property
    def linked_item_type(self):
        """Return the type of linked item."""
        if self.pending_item_id:
            return 'Pendência'
        elif self.non_conformity_id:
            return 'Não Conformidade'
        elif self.bug_id:
            return 'Bug'
        elif self.risk_id:
            return 'Risco'
        return None

    @property
    def linked_item(self):
        """Return the linked item object."""
        if self.pending_item_id:
            return self.pending_item
        elif self.non_conformity_id:
            return self.non_conformity
        elif self.bug_id:
            return self.bug
        elif self.risk_id:
            return self.risk
        return None


# Helper function to get current tenant
def get_current_tenant_id():
    """Get the current tenant ID from the logged-in user."""
    from flask_login import current_user
    if current_user.is_authenticated and current_user.tenant_id:
        return current_user.tenant_id
    return None
