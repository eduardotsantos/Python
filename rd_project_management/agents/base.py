"""
Base Agent Framework for Orion Autônomos PMO.
All specialized agents inherit from BaseAgent.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from enum import Enum
import json


class Severity(Enum):
    """Severity levels for insights and alerts."""
    INFO = 'info'
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    CRITICAL = 'critical'


class HealthStatus(Enum):
    """Project health status indicators."""
    HEALTHY = 'healthy'      # 🟢
    ATTENTION = 'attention'  # 🟡
    CRITICAL = 'critical'    # 🔴


class ActionType(Enum):
    """Types of actions agents can suggest."""
    SCHEDULE_MEETING = 'schedule_meeting'
    CREATE_RISK = 'create_risk'
    CREATE_PENDING = 'create_pending'
    CREATE_NC = 'create_nc'
    CREATE_ACTION = 'create_action'
    SEND_NOTIFICATION = 'send_notification'
    GENERATE_REPORT = 'generate_report'
    REPLAN_SCHEDULE = 'replan_schedule'
    REALLOCATE_RESOURCE = 'reallocate_resource'
    CREATE_SCENARIO = 'create_scenario'
    UPDATE_STATUS = 'update_status'
    ESCALATE = 'escalate'


@dataclass
class ActionSuggestion:
    """Represents an action that an agent suggests."""
    action_type: ActionType
    title: str
    description: str
    priority: Severity = Severity.MEDIUM
    data: Dict[str, Any] = field(default_factory=dict)
    auto_executable: bool = False
    requires_approval: bool = True
    agent_name: str = ''
    project_id: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'action_type': self.action_type.value,
            'title': self.title,
            'description': self.description,
            'priority': self.priority.value,
            'data': self.data,
            'auto_executable': self.auto_executable,
            'requires_approval': self.requires_approval,
            'agent_name': self.agent_name,
            'project_id': self.project_id,
            'created_at': self.created_at.isoformat()
        }


@dataclass
class Insight:
    """Represents an insight/finding from an agent analysis."""
    title: str
    description: str
    severity: Severity
    category: str
    project_id: Optional[int] = None
    project_name: Optional[str] = None
    metric_name: Optional[str] = None
    metric_value: Optional[float] = None
    metric_threshold: Optional[float] = None
    recommendation: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'title': self.title,
            'description': self.description,
            'severity': self.severity.value,
            'category': self.category,
            'project_id': self.project_id,
            'project_name': self.project_name,
            'metric_name': self.metric_name,
            'metric_value': self.metric_value,
            'metric_threshold': self.metric_threshold,
            'recommendation': self.recommendation,
            'data': self.data
        }


@dataclass
class AgentResult:
    """Result of an agent execution."""
    agent_name: str
    success: bool
    execution_time: float
    insights: List[Insight] = field(default_factory=list)
    actions: List[ActionSuggestion] = field(default_factory=list)
    summary: str = ''
    health_status: Optional[HealthStatus] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    executed_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def has_critical_insights(self) -> bool:
        return any(i.severity == Severity.CRITICAL for i in self.insights)

    @property
    def has_high_insights(self) -> bool:
        return any(i.severity in [Severity.HIGH, Severity.CRITICAL] for i in self.insights)

    @property
    def critical_count(self) -> int:
        return sum(1 for i in self.insights if i.severity == Severity.CRITICAL)

    @property
    def high_count(self) -> int:
        return sum(1 for i in self.insights if i.severity == Severity.HIGH)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'agent_name': self.agent_name,
            'success': self.success,
            'execution_time': self.execution_time,
            'insights': [i.to_dict() for i in self.insights],
            'actions': [a.to_dict() for a in self.actions],
            'summary': self.summary,
            'health_status': self.health_status.value if self.health_status else None,
            'metrics': self.metrics,
            'errors': self.errors,
            'executed_at': self.executed_at.isoformat(),
            'critical_count': self.critical_count,
            'high_count': self.high_count
        }


class BaseAgent(ABC):
    """
    Base class for all PMO agents.
    Each agent has a specific responsibility and analysis capability.
    """

    def __init__(self, tenant_id: int, db_session=None):
        self.tenant_id = tenant_id
        self.db = db_session
        self._start_time = None

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name identifier for the agent."""
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable display name."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Description of what the agent does."""
        pass

    @property
    def icon(self) -> str:
        """Bootstrap icon class for the agent."""
        return 'bi-robot'

    @property
    def color(self) -> str:
        """Color theme for the agent (Bootstrap color)."""
        return 'primary'

    def _start_execution(self):
        """Mark start of execution for timing."""
        self._start_time = datetime.utcnow()

    def _get_execution_time(self) -> float:
        """Get execution time in seconds."""
        if self._start_time:
            return (datetime.utcnow() - self._start_time).total_seconds()
        return 0.0

    @abstractmethod
    def analyze(self, project_id: Optional[int] = None) -> AgentResult:
        """
        Run the agent's analysis.
        If project_id is provided, analyze only that project.
        Otherwise, analyze all projects for the tenant.
        """
        pass

    def analyze_all_projects(self) -> AgentResult:
        """Analyze all projects and aggregate results."""
        return self.analyze(project_id=None)

    def analyze_project(self, project_id: int) -> AgentResult:
        """Analyze a specific project."""
        return self.analyze(project_id=project_id)

    def create_insight(
        self,
        title: str,
        description: str,
        severity: Severity,
        category: str,
        project_id: Optional[int] = None,
        project_name: Optional[str] = None,
        **kwargs
    ) -> Insight:
        """Helper to create an insight."""
        return Insight(
            title=title,
            description=description,
            severity=severity,
            category=category,
            project_id=project_id,
            project_name=project_name,
            **kwargs
        )

    def suggest_action(
        self,
        action_type: ActionType,
        title: str,
        description: str,
        priority: Severity = Severity.MEDIUM,
        project_id: Optional[int] = None,
        **kwargs
    ) -> ActionSuggestion:
        """Helper to create an action suggestion."""
        return ActionSuggestion(
            action_type=action_type,
            title=title,
            description=description,
            priority=priority,
            agent_name=self.name,
            project_id=project_id,
            **kwargs
        )

    def create_result(
        self,
        success: bool = True,
        insights: List[Insight] = None,
        actions: List[ActionSuggestion] = None,
        summary: str = '',
        health_status: HealthStatus = None,
        metrics: Dict[str, Any] = None,
        errors: List[str] = None
    ) -> AgentResult:
        """Helper to create an agent result."""
        return AgentResult(
            agent_name=self.name,
            success=success,
            execution_time=self._get_execution_time(),
            insights=insights or [],
            actions=actions or [],
            summary=summary,
            health_status=health_status,
            metrics=metrics or {},
            errors=errors or []
        )


def severity_emoji(severity: Severity) -> str:
    """Get emoji for severity level."""
    mapping = {
        Severity.INFO: 'ℹ️',
        Severity.LOW: '🔵',
        Severity.MEDIUM: '🟡',
        Severity.HIGH: '🟠',
        Severity.CRITICAL: '🔴'
    }
    return mapping.get(severity, '⚪')


def health_emoji(status: HealthStatus) -> str:
    """Get emoji for health status."""
    mapping = {
        HealthStatus.HEALTHY: '🟢',
        HealthStatus.ATTENTION: '🟡',
        HealthStatus.CRITICAL: '🔴'
    }
    return mapping.get(status, '⚪')
