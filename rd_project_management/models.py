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
    logo_url = db.Column(db.String(500))
    plan = db.Column(db.String(50), default='basic')  # basic, professional, enterprise
    max_users = db.Column(db.Integer, default=5)
    max_projects = db.Column(db.Integer, default=10)
    active = db.Column(db.Boolean, default=True)
    expires_at = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=True)  # Null for super admin
    username = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), default='user')  # superadmin, admin, manager, user
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    active = db.Column(db.Boolean, default=True)

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


class Project(db.Model):
    __tablename__ = 'projects'
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
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


class Milestone(db.Model):
    __tablename__ = 'milestones'
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    progress = db.Column(db.Integer, default=0)
    status = db.Column(db.String(50), default='Pendente')
    order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


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


# Helper function to get current tenant
def get_current_tenant_id():
    """Get the current tenant ID from the logged-in user."""
    from flask_login import current_user
    if current_user.is_authenticated and current_user.tenant_id:
        return current_user.tenant_id
    return None
