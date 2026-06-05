"""
PMO Orchestrator - Coordinates all agents and provides Daily Executive AI.
This is the central intelligence that runs agents, aggregates results, and takes action.
"""
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
import json
import logging

from .base import (
    BaseAgent, AgentResult, Insight, ActionSuggestion,
    Severity, HealthStatus, ActionType, health_emoji, severity_emoji
)

logger = logging.getLogger(__name__)


@dataclass
class ComplianceSummary:
    """Summary of compliance items for briefing."""
    total_risks: int = 0
    open_risks: int = 0
    critical_risks: int = 0
    total_pending: int = 0
    overdue_pending: int = 0
    total_bugs: int = 0
    open_bugs: int = 0
    critical_bugs: int = 0
    total_ncs: int = 0
    open_ncs: int = 0
    total_actions: int = 0
    pending_actions: int = 0
    risks_by_project: List[Dict] = field(default_factory=list)
    pending_by_project: List[Dict] = field(default_factory=list)
    bugs_by_project: List[Dict] = field(default_factory=list)
    critical_items: List[Dict] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            'total_risks': self.total_risks,
            'open_risks': self.open_risks,
            'critical_risks': self.critical_risks,
            'total_pending': self.total_pending,
            'overdue_pending': self.overdue_pending,
            'total_bugs': self.total_bugs,
            'open_bugs': self.open_bugs,
            'critical_bugs': self.critical_bugs,
            'total_ncs': self.total_ncs,
            'open_ncs': self.open_ncs,
            'total_actions': self.total_actions,
            'pending_actions': self.pending_actions,
            'risks_by_project': self.risks_by_project,
            'pending_by_project': self.pending_by_project,
            'bugs_by_project': self.bugs_by_project,
            'critical_items': self.critical_items
        }


@dataclass
class ActivityAnalysis:
    """Analysis of a project activity/milestone."""
    milestone_id: int
    project_id: int
    project_name: str
    title: str
    status: str
    progress: int
    start_date: date
    end_date: date
    is_late: bool
    days_variance: int  # positive = late, negative = ahead
    planned_hours: float
    actual_hours: float
    planned_cost: float
    actual_cost: float
    cost_variance: float  # percentage
    responsibles: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            'milestone_id': self.milestone_id,
            'project_id': self.project_id,
            'project_name': self.project_name,
            'title': self.title,
            'status': self.status,
            'progress': self.progress,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'is_late': self.is_late,
            'days_variance': self.days_variance,
            'planned_hours': self.planned_hours,
            'actual_hours': self.actual_hours,
            'planned_cost': self.planned_cost,
            'actual_cost': self.actual_cost,
            'cost_variance': self.cost_variance,
            'responsibles': self.responsibles
        }


@dataclass
class ProjectSummary:
    """Summary of a project for briefing."""
    project_id: int
    code: str
    title: str
    status: str
    budget: float
    spent: float
    budget_variance: float
    progress: float
    schedule_status: str  # on_track, at_risk, late
    total_milestones: int
    completed_milestones: int
    late_milestones: int
    upcoming_milestones: List[Dict] = field(default_factory=list)
    recent_milestones: List[Dict] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            'project_id': self.project_id,
            'code': self.code,
            'title': self.title,
            'status': self.status,
            'budget': self.budget,
            'spent': self.spent,
            'budget_variance': self.budget_variance,
            'progress': self.progress,
            'schedule_status': self.schedule_status,
            'total_milestones': self.total_milestones,
            'completed_milestones': self.completed_milestones,
            'late_milestones': self.late_milestones,
            'upcoming_milestones': self.upcoming_milestones,
            'recent_milestones': self.recent_milestones
        }


@dataclass
class DailyBriefing:
    """Daily executive briefing structure."""
    date: date
    tenant_id: int
    overall_status: HealthStatus
    summary: str
    agent_results: List[AgentResult] = field(default_factory=list)
    priority_items: List[Dict] = field(default_factory=list)
    recommended_actions: List[ActionSuggestion] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    generated_at: datetime = field(default_factory=datetime.utcnow)
    # New detailed sections
    project_summaries: List[ProjectSummary] = field(default_factory=list)
    past_activities: List[ActivityAnalysis] = field(default_factory=list)
    upcoming_activities: List[ActivityAnalysis] = field(default_factory=list)
    cost_analysis: Dict[str, Any] = field(default_factory=dict)
    compliance_summary: ComplianceSummary = field(default_factory=ComplianceSummary)
    user_name: str = "Usuário"

    def to_dict(self) -> Dict:
        return {
            'date': self.date.isoformat(),
            'tenant_id': self.tenant_id,
            'overall_status': self.overall_status.value,
            'summary': self.summary,
            'agent_results': [r.to_dict() for r in self.agent_results],
            'priority_items': self.priority_items,
            'recommended_actions': [a.to_dict() for a in self.recommended_actions],
            'metrics': self.metrics,
            'generated_at': self.generated_at.isoformat(),
            'project_summaries': [p.to_dict() for p in self.project_summaries],
            'past_activities': [a.to_dict() for a in self.past_activities],
            'upcoming_activities': [a.to_dict() for a in self.upcoming_activities],
            'cost_analysis': self.cost_analysis,
            'compliance_summary': self.compliance_summary.to_dict() if self.compliance_summary else {},
            'user_name': self.user_name
        }


class PMOOrchestrator:
    """
    Orquestrador do PMO Autônomo.
    Coordinates agent execution, aggregates results, and drives actions.
    """

    def __init__(self, tenant_id: int, db_session=None):
        self.tenant_id = tenant_id
        self.db = db_session
        self._agents = {}
        self._initialize_agents()

    def _initialize_agents(self):
        """Initialize all PMO agents."""
        from .health_agent import ProjectHealthAgent
        from .risk_agent import RiskAgent
        from .financial_agent import FinancialAgent
        from .schedule_agent import ScheduleAgent
        from .resource_agent import ResourceAgent
        from .quality_agent import QualityAgent
        from .compliance_agent import ComplianceAgent
        from .communication_agent import CommunicationAgent
        from .lessons_agent import LessonsLearnedAgent
        from .advisor_agent import ProjectAdvisorAgent
        from .minutes_reader import MinutesReaderAgent

        agent_classes = [
            ProjectHealthAgent,
            RiskAgent,
            FinancialAgent,
            ScheduleAgent,
            ResourceAgent,
            QualityAgent,
            ComplianceAgent,
            CommunicationAgent,
            LessonsLearnedAgent,
            ProjectAdvisorAgent,
            MinutesReaderAgent
        ]

        for agent_class in agent_classes:
            agent = agent_class(self.tenant_id, self.db)
            self._agents[agent.name] = agent

    @property
    def agents(self) -> Dict[str, BaseAgent]:
        """Get all registered agents."""
        return self._agents

    def get_agent(self, name: str) -> Optional[BaseAgent]:
        """Get a specific agent by name."""
        return self._agents.get(name)

    def run_agent(self, agent_name: str, project_id: Optional[int] = None) -> AgentResult:
        """Run a single agent."""
        agent = self._agents.get(agent_name)
        if not agent:
            raise ValueError(f"Agent '{agent_name}' not found")

        try:
            result = agent.analyze(project_id)
            self._log_agent_run(agent_name, result)
            return result
        except Exception as e:
            logger.error(f"Error running agent {agent_name}: {e}")
            return AgentResult(
                agent_name=agent_name,
                success=False,
                execution_time=0,
                errors=[str(e)]
            )

    def run_all_agents(self, project_id: Optional[int] = None) -> List[AgentResult]:
        """Run all agents and collect results."""
        results = []

        priority_order = [
            'health_agent',
            'financial_agent',
            'schedule_agent',
            'resource_agent',
            'risk_agent',
            'quality_agent',
            'compliance_agent',
            'minutes_reader',
            'lessons_agent',
            'advisor_agent',
            'communication_agent'
        ]

        for agent_name in priority_order:
            if agent_name in self._agents:
                result = self.run_agent(agent_name, project_id)
                results.append(result)

        return results

    def generate_daily_briefing(self, user_name: str = "Usuário") -> DailyBriefing:
        """
        Generate the Daily Executive AI briefing.
        This runs every morning to provide executive summary.
        """
        logger.info(f"Generating daily briefing for tenant {self.tenant_id}")

        results = self.run_all_agents()

        overall_status = self._determine_overall_status(results)
        priority_items = self._extract_priority_items(results)
        recommended_actions = self._aggregate_actions(results)
        metrics = self._aggregate_metrics(results)

        # New detailed analysis
        project_summaries = self._analyze_projects()
        past_activities = self._analyze_past_activities()
        upcoming_activities = self._analyze_upcoming_activities()
        cost_analysis = self._analyze_costs()
        compliance_summary = self._analyze_compliance()

        summary = self._generate_executive_summary(results, overall_status, user_name, compliance_summary)

        briefing = DailyBriefing(
            date=date.today(),
            tenant_id=self.tenant_id,
            overall_status=overall_status,
            summary=summary,
            agent_results=results,
            priority_items=priority_items,
            recommended_actions=recommended_actions[:10],
            metrics=metrics,
            project_summaries=project_summaries,
            past_activities=past_activities,
            upcoming_activities=upcoming_activities,
            cost_analysis=cost_analysis,
            compliance_summary=compliance_summary,
            user_name=user_name
        )

        return briefing

    def _analyze_projects(self) -> List[ProjectSummary]:
        """Analyze all active projects with cost and schedule details."""
        from models import Project, Milestone, Expense, Timesheet, Resource

        summaries = []
        today = date.today()

        projects = Project.query.filter_by(tenant_id=self.tenant_id).filter(
            Project.status.in_(['Em Execução', 'Em Andamento', 'Planejamento', 'Em execução'])
        ).all()

        for project in projects:
            # Get milestones
            milestones = Milestone.query.filter_by(
                tenant_id=self.tenant_id,
                project_id=project.id
            ).all()

            total_ms = len(milestones)
            completed_ms = sum(1 for m in milestones if m.status in ['Concluído', 'Concluída', 'Finalizado'])
            late_ms = sum(1 for m in milestones if m.end_date < today and m.status not in ['Concluído', 'Concluída', 'Finalizado'])

            # Calculate progress
            if total_ms > 0:
                progress = sum(m.progress or 0 for m in milestones) / total_ms
            else:
                progress = 0

            # Calculate expenses
            expenses = Expense.query.filter_by(
                tenant_id=self.tenant_id,
                project_id=project.id
            ).all()
            spent = sum(e.amount for e in expenses)

            # Calculate labor cost from timesheets
            timesheets = Timesheet.query.filter_by(
                tenant_id=self.tenant_id,
                project_id=project.id
            ).all()

            labor_cost = 0
            for ts in timesheets:
                if ts.resource and ts.resource.hourly_cost:
                    labor_cost += ts.hours * ts.resource.hourly_cost

            total_spent = spent + labor_cost
            budget = project.budget or 0
            budget_variance = ((total_spent - budget) / budget * 100) if budget > 0 else 0

            # Determine schedule status
            if late_ms > 0:
                schedule_status = 'late'
            elif late_ms == 0 and total_ms > 0 and completed_ms < total_ms:
                # Check if any milestone is at risk (ending within 7 days)
                at_risk = any(m.end_date <= today + timedelta(days=7) and m.status not in ['Concluído', 'Concluída', 'Finalizado'] for m in milestones)
                schedule_status = 'at_risk' if at_risk else 'on_track'
            else:
                schedule_status = 'on_track'

            # Get upcoming milestones (next 14 days)
            upcoming = [
                {
                    'id': m.id,
                    'title': m.title,
                    'end_date': m.end_date.isoformat(),
                    'progress': m.progress,
                    'responsibles': m.responsible_names
                }
                for m in milestones
                if m.end_date >= today and m.end_date <= today + timedelta(days=14)
                and m.status not in ['Concluído', 'Concluída', 'Finalizado']
            ]

            # Get recent completed milestones (last 7 days)
            recent = [
                {
                    'id': m.id,
                    'title': m.title,
                    'end_date': m.end_date.isoformat(),
                    'progress': m.progress
                }
                for m in milestones
                if m.status in ['Concluído', 'Concluída', 'Finalizado']
                and m.end_date >= today - timedelta(days=7)
            ]

            summaries.append(ProjectSummary(
                project_id=project.id,
                code=project.code,
                title=project.title,
                status=project.status,
                budget=budget,
                spent=total_spent,
                budget_variance=budget_variance,
                progress=progress,
                schedule_status=schedule_status,
                total_milestones=total_ms,
                completed_milestones=completed_ms,
                late_milestones=late_ms,
                upcoming_milestones=upcoming[:5],
                recent_milestones=recent[:5]
            ))

        return summaries

    def _analyze_past_activities(self, days: int = 7) -> List[ActivityAnalysis]:
        """Analyze activities completed or worked on in the past N days."""
        from models import Milestone, Project, Timesheet, MilestoneResource

        activities = []
        today = date.today()
        start_period = today - timedelta(days=days)

        # Get milestones with recent activity
        milestones = Milestone.query.filter(
            Milestone.tenant_id == self.tenant_id
        ).join(Project).filter(
            Project.status.in_(['Em Execução', 'Em Andamento', 'Em execução'])
        ).all()

        for ms in milestones:
            # Check if milestone has recent timesheets
            timesheets = Timesheet.query.filter(
                Timesheet.milestone_id == ms.id,
                Timesheet.date >= start_period,
                Timesheet.date <= today
            ).all()

            if not timesheets and ms.end_date < start_period:
                continue

            # Calculate planned hours from resource allocations
            planned_hours = 0
            for ra in ms.resource_assignments:
                if ra.resource and ra.resource.hours_allocated:
                    planned_hours += ra.resource.hours_allocated * (ra.allocation / 100)

            # Calculate actual hours and cost
            actual_hours = sum(ts.hours for ts in timesheets)
            actual_cost = 0
            for ts in timesheets:
                if ts.resource and ts.resource.hourly_cost:
                    actual_cost += ts.hours * ts.resource.hourly_cost

            # Calculate planned cost
            planned_cost = 0
            for ra in ms.resource_assignments:
                if ra.resource and ra.resource.hourly_cost:
                    expected_hours = ra.resource.hours_allocated * (ra.allocation / 100) if ra.resource.hours_allocated else 0
                    planned_cost += expected_hours * ra.resource.hourly_cost

            # Calculate variance
            cost_variance = ((actual_cost - planned_cost) / planned_cost * 100) if planned_cost > 0 else 0

            # Check if late
            is_late = ms.end_date < today and ms.status not in ['Concluído', 'Concluída', 'Finalizado']
            days_variance = (today - ms.end_date).days if is_late else 0

            # Get responsibles
            responsibles = [ra.resource.name for ra in ms.resource_assignments if ra.resource]

            activities.append(ActivityAnalysis(
                milestone_id=ms.id,
                project_id=ms.project_id,
                project_name=ms.project.title if ms.project else '',
                title=ms.title,
                status=ms.status,
                progress=ms.progress or 0,
                start_date=ms.start_date,
                end_date=ms.end_date,
                is_late=is_late,
                days_variance=days_variance,
                planned_hours=planned_hours,
                actual_hours=actual_hours,
                planned_cost=planned_cost,
                actual_cost=actual_cost,
                cost_variance=cost_variance,
                responsibles=responsibles
            ))

        # Sort by recent activity
        activities.sort(key=lambda a: (not a.is_late, -a.actual_hours))
        return activities[:15]

    def _analyze_upcoming_activities(self, days: int = 14) -> List[ActivityAnalysis]:
        """Analyze activities scheduled for the next N days."""
        from models import Milestone, Project, MilestoneResource

        activities = []
        today = date.today()
        end_period = today + timedelta(days=days)

        milestones = Milestone.query.filter(
            Milestone.tenant_id == self.tenant_id,
            Milestone.end_date >= today,
            Milestone.end_date <= end_period,
            Milestone.status.notin_(['Concluído', 'Concluída', 'Finalizado'])
        ).join(Project).filter(
            Project.status.in_(['Em Execução', 'Em Andamento', 'Em execução', 'Planejamento'])
        ).order_by(Milestone.end_date).all()

        for ms in milestones:
            # Calculate planned hours and cost
            planned_hours = 0
            planned_cost = 0
            responsibles = []

            for ra in ms.resource_assignments:
                if ra.resource:
                    responsibles.append(ra.resource.name)
                    if ra.resource.hours_allocated:
                        hours = ra.resource.hours_allocated * (ra.allocation / 100)
                        planned_hours += hours
                        if ra.resource.hourly_cost:
                            planned_cost += hours * ra.resource.hourly_cost

            # Calculate actual hours so far
            actual_hours = sum(ts.hours for ts in ms.timesheets) if ms.timesheets else 0
            actual_cost = 0
            for ts in ms.timesheets:
                if ts.resource and ts.resource.hourly_cost:
                    actual_cost += ts.hours * ts.resource.hourly_cost

            cost_variance = ((actual_cost - planned_cost) / planned_cost * 100) if planned_cost > 0 else 0

            days_until = (ms.end_date - today).days

            activities.append(ActivityAnalysis(
                milestone_id=ms.id,
                project_id=ms.project_id,
                project_name=ms.project.title if ms.project else '',
                title=ms.title,
                status=ms.status,
                progress=ms.progress or 0,
                start_date=ms.start_date,
                end_date=ms.end_date,
                is_late=False,
                days_variance=-days_until,  # Negative = days remaining
                planned_hours=planned_hours,
                actual_hours=actual_hours,
                planned_cost=planned_cost,
                actual_cost=actual_cost,
                cost_variance=cost_variance,
                responsibles=responsibles
            ))

        return activities[:15]

    def _analyze_costs(self) -> Dict[str, Any]:
        """Analyze overall cost situation across all projects."""
        from models import Project, Expense, Timesheet

        today = date.today()

        projects = Project.query.filter_by(tenant_id=self.tenant_id).filter(
            Project.status.in_(['Em Execução', 'Em Andamento', 'Em execução'])
        ).all()

        total_budget = 0
        total_spent = 0
        total_labor = 0
        total_expenses = 0
        projects_over_budget = []
        projects_under_budget = []

        for project in projects:
            budget = project.budget or 0
            total_budget += budget

            # Expenses
            expenses = Expense.query.filter_by(
                tenant_id=self.tenant_id,
                project_id=project.id
            ).all()
            project_expenses = sum(e.amount for e in expenses)
            total_expenses += project_expenses

            # Labor from timesheets
            timesheets = Timesheet.query.filter_by(
                tenant_id=self.tenant_id,
                project_id=project.id
            ).all()

            project_labor = 0
            for ts in timesheets:
                if ts.resource and ts.resource.hourly_cost:
                    project_labor += ts.hours * ts.resource.hourly_cost
            total_labor += project_labor

            project_total = project_expenses + project_labor
            total_spent += project_total

            variance = ((project_total - budget) / budget * 100) if budget > 0 else 0

            if variance > 10:
                projects_over_budget.append({
                    'project_id': project.id,
                    'code': project.code,
                    'title': project.title,
                    'budget': budget,
                    'spent': project_total,
                    'variance': variance
                })
            elif variance < -20 and budget > 0:
                projects_under_budget.append({
                    'project_id': project.id,
                    'code': project.code,
                    'title': project.title,
                    'budget': budget,
                    'spent': project_total,
                    'variance': variance
                })

        # Calculate this month's spending
        first_of_month = today.replace(day=1)
        month_expenses = Expense.query.filter(
            Expense.tenant_id == self.tenant_id,
            Expense.date >= first_of_month
        ).all()
        month_spent = sum(e.amount for e in month_expenses)

        return {
            'total_budget': total_budget,
            'total_spent': total_spent,
            'total_labor': total_labor,
            'total_expenses': total_expenses,
            'budget_variance': ((total_spent - total_budget) / total_budget * 100) if total_budget > 0 else 0,
            'month_spent': month_spent,
            'projects_over_budget': sorted(projects_over_budget, key=lambda x: -x['variance'])[:5],
            'projects_under_budget': sorted(projects_under_budget, key=lambda x: x['variance'])[:5],
            'labor_percentage': (total_labor / total_spent * 100) if total_spent > 0 else 0
        }

    def _analyze_compliance(self) -> ComplianceSummary:
        """Analyze compliance items: risks, pending items, bugs, NCs, corrective actions."""
        from models import Risk, PendingItem, NonConformity, Bug, CorrectiveAction, Project

        today = date.today()
        summary = ComplianceSummary()

        # Analyze Risks
        risks = Risk.query.filter_by(tenant_id=self.tenant_id).all()
        summary.total_risks = len(risks)
        summary.open_risks = sum(1 for r in risks if r.status not in ['Fechado', 'Mitigado', 'Encerrado'])
        summary.critical_risks = sum(1 for r in risks if r.probability >= 4 and r.impact >= 4 and r.status not in ['Fechado', 'Mitigado', 'Encerrado'])

        # Group risks by project
        risks_by_proj = {}
        for r in risks:
            if r.status not in ['Fechado', 'Mitigado', 'Encerrado']:
                if r.project_id not in risks_by_proj:
                    risks_by_proj[r.project_id] = {'project_id': r.project_id, 'project_name': '', 'count': 0, 'critical': 0}
                risks_by_proj[r.project_id]['count'] += 1
                if r.probability >= 4 and r.impact >= 4:
                    risks_by_proj[r.project_id]['critical'] += 1
                if r.project:
                    risks_by_proj[r.project_id]['project_name'] = r.project.title

        summary.risks_by_project = sorted(risks_by_proj.values(), key=lambda x: -x['critical'])[:5]

        # Analyze Pending Items
        pending = PendingItem.query.filter_by(tenant_id=self.tenant_id).all()
        summary.total_pending = len(pending)
        summary.overdue_pending = sum(1 for p in pending if p.due_date and p.due_date < today and p.status not in ['Concluída', 'Fechada', 'Resolvida'])

        # Group pending by project
        pending_by_proj = {}
        for p in pending:
            if p.status not in ['Concluída', 'Fechada', 'Resolvida']:
                if p.project_id not in pending_by_proj:
                    pending_by_proj[p.project_id] = {'project_id': p.project_id, 'project_name': '', 'count': 0, 'overdue': 0}
                pending_by_proj[p.project_id]['count'] += 1
                if p.due_date and p.due_date < today:
                    pending_by_proj[p.project_id]['overdue'] += 1
                if p.project:
                    pending_by_proj[p.project_id]['project_name'] = p.project.title

        summary.pending_by_project = sorted(pending_by_proj.values(), key=lambda x: -x['overdue'])[:5]

        # Analyze Bugs
        bugs = Bug.query.filter_by(tenant_id=self.tenant_id).all()
        summary.total_bugs = len(bugs)
        summary.open_bugs = sum(1 for b in bugs if b.status not in ['Fechado', 'Resolvido', 'Encerrado'])
        summary.critical_bugs = sum(1 for b in bugs if b.severity in ['Crítico', 'Crítica', 'Critical'] and b.status not in ['Fechado', 'Resolvido', 'Encerrado'])

        # Group bugs by project
        bugs_by_proj = {}
        for b in bugs:
            if b.status not in ['Fechado', 'Resolvido', 'Encerrado']:
                if b.project_id not in bugs_by_proj:
                    bugs_by_proj[b.project_id] = {'project_id': b.project_id, 'project_name': '', 'count': 0, 'critical': 0}
                bugs_by_proj[b.project_id]['count'] += 1
                if b.severity in ['Crítico', 'Crítica', 'Critical']:
                    bugs_by_proj[b.project_id]['critical'] += 1
                if b.project:
                    bugs_by_proj[b.project_id]['project_name'] = b.project.title

        summary.bugs_by_project = sorted(bugs_by_proj.values(), key=lambda x: -x['critical'])[:5]

        # Analyze Non-Conformities
        ncs = NonConformity.query.filter_by(tenant_id=self.tenant_id).all()
        summary.total_ncs = len(ncs)
        summary.open_ncs = sum(1 for nc in ncs if nc.status not in ['Fechada', 'Encerrada', 'Resolvida'])

        # Analyze Corrective Actions
        actions = CorrectiveAction.query.filter_by(tenant_id=self.tenant_id).all()
        summary.total_actions = len(actions)
        summary.pending_actions = sum(1 for a in actions if a.status not in ['Concluída', 'Implementada', 'Fechada'])

        # Collect critical items for priority display
        critical_items = []

        # Critical risks
        for r in risks:
            if r.probability >= 4 and r.impact >= 4 and r.status not in ['Fechado', 'Mitigado', 'Encerrado']:
                critical_items.append({
                    'type': 'Risco',
                    'type_icon': '⚠️',
                    'title': r.title,
                    'project_name': r.project.title if r.project else 'N/A',
                    'project_id': r.project_id,
                    'severity': f"P{r.probability}xI{r.impact}",
                    'status': r.status,
                    'id': r.id
                })

        # Overdue pending items
        for p in pending:
            if p.due_date and p.due_date < today and p.status not in ['Concluída', 'Fechada', 'Resolvida']:
                days_overdue = (today - p.due_date).days
                critical_items.append({
                    'type': 'Pendência',
                    'type_icon': '📋',
                    'title': p.title,
                    'project_name': p.project.title if p.project else 'N/A',
                    'project_id': p.project_id,
                    'severity': f"{days_overdue} dias atrasada",
                    'status': p.status,
                    'id': p.id
                })

        # Critical bugs
        for b in bugs:
            if b.severity in ['Crítico', 'Crítica', 'Critical'] and b.status not in ['Fechado', 'Resolvido', 'Encerrado']:
                critical_items.append({
                    'type': 'Bug',
                    'type_icon': '🐛',
                    'title': b.title,
                    'project_name': b.project.title if b.project else 'N/A',
                    'project_id': b.project_id,
                    'severity': b.severity,
                    'status': b.status,
                    'id': b.id
                })

        # Open NCs
        for nc in ncs:
            if nc.status not in ['Fechada', 'Encerrada', 'Resolvida']:
                critical_items.append({
                    'type': 'NC',
                    'type_icon': '❌',
                    'title': nc.title,
                    'project_name': nc.project.title if nc.project else 'N/A',
                    'project_id': nc.project_id,
                    'severity': nc.severity if hasattr(nc, 'severity') and nc.severity else 'N/A',
                    'status': nc.status,
                    'id': nc.id
                })

        summary.critical_items = critical_items[:15]

        return summary

    def _determine_overall_status(self, results: List[AgentResult]) -> HealthStatus:
        """Determine overall portfolio status from agent results."""
        critical_count = sum(1 for r in results if r.health_status == HealthStatus.CRITICAL)
        attention_count = sum(1 for r in results if r.health_status == HealthStatus.ATTENTION)

        if critical_count > 0:
            return HealthStatus.CRITICAL
        elif attention_count >= 3:
            return HealthStatus.CRITICAL
        elif attention_count > 0:
            return HealthStatus.ATTENTION
        return HealthStatus.HEALTHY

    def _extract_priority_items(self, results: List[AgentResult]) -> List[Dict]:
        """Extract highest priority items from all results."""
        priority_items = []

        for result in results:
            for insight in result.insights:
                if insight.severity in [Severity.CRITICAL, Severity.HIGH]:
                    priority_items.append({
                        'agent': result.agent_name,
                        'title': insight.title,
                        'description': insight.description,
                        'severity': insight.severity.value,
                        'project_id': insight.project_id,
                        'project_name': insight.project_name,
                        'recommendation': insight.recommendation
                    })

        priority_items.sort(key=lambda x: (
            0 if x['severity'] == 'critical' else 1
        ))

        return priority_items[:10]

    def _aggregate_actions(self, results: List[AgentResult]) -> List[ActionSuggestion]:
        """Aggregate and prioritize actions from all agents."""
        all_actions = []

        for result in results:
            all_actions.extend(result.actions)

        all_actions.sort(key=lambda a: (
            0 if a.priority == Severity.CRITICAL else
            1 if a.priority == Severity.HIGH else
            2 if a.priority == Severity.MEDIUM else 3
        ))

        return all_actions

    def _aggregate_metrics(self, results: List[AgentResult]) -> Dict:
        """Aggregate metrics from all agents."""
        metrics = {
            'total_insights': 0,
            'critical_insights': 0,
            'high_insights': 0,
            'total_actions': 0,
            'agents_healthy': 0,
            'agents_attention': 0,
            'agents_critical': 0,
            'by_agent': {}
        }

        for result in results:
            metrics['total_insights'] += len(result.insights)
            metrics['critical_insights'] += result.critical_count
            metrics['high_insights'] += result.high_count
            metrics['total_actions'] += len(result.actions)

            if result.health_status == HealthStatus.HEALTHY:
                metrics['agents_healthy'] += 1
            elif result.health_status == HealthStatus.ATTENTION:
                metrics['agents_attention'] += 1
            elif result.health_status == HealthStatus.CRITICAL:
                metrics['agents_critical'] += 1

            metrics['by_agent'][result.agent_name] = {
                'status': result.health_status.value if result.health_status else 'unknown',
                'insights': len(result.insights),
                'actions': len(result.actions),
                'summary': result.summary
            }

        return metrics

    def _generate_executive_summary(
        self,
        results: List[AgentResult],
        status: HealthStatus,
        user_name: str,
        compliance_summary: ComplianceSummary = None
    ) -> str:
        """Generate human-readable executive summary."""
        today = date.today()
        greeting = "Bom dia" if datetime.now().hour < 12 else "Boa tarde" if datetime.now().hour < 18 else "Boa noite"

        summary = f"""
{greeting}, {user_name}.

📊 Análise diária concluída em {today.strftime('%d/%m/%Y')}.

"""
        healthy = sum(1 for r in results if r.health_status == HealthStatus.HEALTHY)
        attention = sum(1 for r in results if r.health_status == HealthStatus.ATTENTION)
        critical = sum(1 for r in results if r.health_status == HealthStatus.CRITICAL)

        summary += f"""SITUAÇÃO GERAL
{health_emoji(status)} Status: {status.value.upper()}

"""

        if status == HealthStatus.CRITICAL:
            summary += f"⚠️ ATENÇÃO: {critical} área(s) crítica(s) identificada(s).\n\n"
        elif status == HealthStatus.ATTENTION:
            summary += f"📋 {attention} área(s) requer(em) atenção.\n\n"
        else:
            summary += "✅ Operações normais em todas as áreas.\n\n"

        # Compliance Summary Section
        if compliance_summary:
            summary += "CENTRAL DE CONFORMIDADE\n"
            summary += "-" * 50 + "\n"
            summary += f"⚠️ Riscos: {compliance_summary.open_risks} abertos"
            if compliance_summary.critical_risks > 0:
                summary += f" ({compliance_summary.critical_risks} críticos!)"
            summary += "\n"
            summary += f"📋 Pendências: {compliance_summary.total_pending - compliance_summary.overdue_pending} em dia"
            if compliance_summary.overdue_pending > 0:
                summary += f", {compliance_summary.overdue_pending} atrasadas!"
            summary += "\n"
            summary += f"🐛 Bugs: {compliance_summary.open_bugs} abertos"
            if compliance_summary.critical_bugs > 0:
                summary += f" ({compliance_summary.critical_bugs} críticos!)"
            summary += "\n"
            summary += f"❌ Não Conformidades: {compliance_summary.open_ncs} abertas\n"
            summary += f"🔧 Ações Corretivas: {compliance_summary.pending_actions} pendentes\n\n"

        summary += "RESUMO POR ÁREA\n"
        summary += "-" * 50 + "\n"

        for result in results:
            if result.health_status:
                emoji = health_emoji(result.health_status)
                agent = self._agents.get(result.agent_name)
                display_name = agent.display_name if agent else result.agent_name
                summary += f"{emoji} {display_name}: {result.summary}\n"

        priority_insights = []
        for result in results:
            for insight in result.insights:
                if insight.severity in [Severity.CRITICAL, Severity.HIGH]:
                    priority_insights.append(insight)

        if priority_insights:
            summary += f"\nPRIORIDADES DO DIA ({len(priority_insights)})\n"
            summary += "-" * 50 + "\n"

            for i, insight in enumerate(priority_insights[:5], 1):
                emoji = severity_emoji(insight.severity)
                summary += f"\n{i}. {emoji} {insight.title}\n"
                if insight.project_name:
                    summary += f"   Projeto: {insight.project_name}\n"
                if insight.recommendation:
                    summary += f"   💡 {insight.recommendation}\n"

        # Add critical compliance items
        if compliance_summary and compliance_summary.critical_items:
            summary += f"\nITENS CRÍTICOS DE CONFORMIDADE ({len(compliance_summary.critical_items)})\n"
            summary += "-" * 50 + "\n"

            for i, item in enumerate(compliance_summary.critical_items[:5], 1):
                summary += f"\n{i}. {item['type_icon']} [{item['type']}] {item['title']}\n"
                summary += f"   Projeto: {item['project_name']} | Status: {item['status']}\n"
                if item['severity']:
                    summary += f"   Severidade: {item['severity']}\n"

        return summary

    def _log_agent_run(self, agent_name: str, result: AgentResult):
        """Log agent execution for audit."""
        logger.info(
            f"Agent {agent_name} completed: "
            f"success={result.success}, "
            f"insights={len(result.insights)}, "
            f"actions={len(result.actions)}, "
            f"time={result.execution_time:.2f}s"
        )

    def execute_action(self, action: ActionSuggestion) -> Dict:
        """
        Execute a suggested action.
        This is where the orchestrator doesn't just recommend - it EXECUTES.
        """
        logger.info(f"Executing action: {action.action_type.value} - {action.title}")

        handlers = {
            ActionType.CREATE_PENDING: self._execute_create_pending,
            ActionType.CREATE_RISK: self._execute_create_risk,
            ActionType.CREATE_NC: self._execute_create_nc,
            ActionType.CREATE_ACTION: self._execute_create_action,
            ActionType.SCHEDULE_MEETING: self._execute_schedule_meeting,
            ActionType.SEND_NOTIFICATION: self._execute_send_notification,
            ActionType.GENERATE_REPORT: self._execute_generate_report,
            ActionType.CREATE_SCENARIO: self._execute_create_scenario,
        }

        handler = handlers.get(action.action_type)
        if handler:
            return handler(action)
        else:
            return {'success': False, 'error': f'No handler for {action.action_type.value}'}

    def _execute_create_pending(self, action: ActionSuggestion) -> Dict:
        """Create a pending item."""
        from models import PendingItem, db

        try:
            item = PendingItem(
                tenant_id=self.tenant_id,
                project_id=action.project_id,
                title=action.data.get('title', action.title),
                description=action.description,
                priority='Média',
                status='Aberta',
                created_at=datetime.utcnow()
            )
            db.session.add(item)
            db.session.commit()
            return {'success': True, 'item_id': item.id}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _execute_create_risk(self, action: ActionSuggestion) -> Dict:
        """Create a risk."""
        from models import Risk, db

        try:
            risk = Risk(
                tenant_id=self.tenant_id,
                project_id=action.project_id,
                title=action.data.get('title', action.title),
                description=action.description,
                probability=3,
                impact=3,
                status='Identificado',
                created_at=datetime.utcnow()
            )
            db.session.add(risk)
            db.session.commit()
            return {'success': True, 'risk_id': risk.id}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _execute_create_nc(self, action: ActionSuggestion) -> Dict:
        """Create a non-conformity."""
        from models import NonConformity, db

        try:
            nc = NonConformity(
                tenant_id=self.tenant_id,
                project_id=action.project_id,
                title=action.data.get('title', action.title),
                description=action.description,
                status='Aberta',
                created_at=datetime.utcnow()
            )
            db.session.add(nc)
            db.session.commit()
            return {'success': True, 'nc_id': nc.id}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _execute_create_action(self, action: ActionSuggestion) -> Dict:
        """Create a corrective action."""
        from models import CorrectiveAction, db

        try:
            ca = CorrectiveAction(
                tenant_id=self.tenant_id,
                project_id=action.project_id,
                description=action.data.get('description', action.description),
                action_type='Corretiva',
                status='Planejada',
                created_at=datetime.utcnow()
            )
            db.session.add(ca)
            db.session.commit()
            return {'success': True, 'action_id': ca.id}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _execute_schedule_meeting(self, action: ActionSuggestion) -> Dict:
        """Schedule a meeting (generates invite content)."""
        meeting_content = {
            'subject': action.title,
            'body': action.description,
            'project_id': action.project_id,
            'suggested_date': (date.today() + timedelta(days=2)).isoformat(),
            'duration': '1 hour'
        }
        return {'success': True, 'meeting': meeting_content, 'action': 'manual_scheduling_required'}

    def _execute_send_notification(self, action: ActionSuggestion) -> Dict:
        """Send notification via email to project team."""
        from models import Project, User, db
        from flask import current_app
        from flask_login import current_user
        from flask_mail import Mail, Message

        try:
            project = Project.query.get(action.project_id) if action.project_id else None
            tenant = project.tenant if project else None

            # Check if tenant has email enabled
            if tenant and not tenant.email_enabled:
                return {'success': False, 'error': 'Email desabilitado para este tenant'}

            # Get recipients (project team with email_alerts enabled)
            recipients = []

            # Always include current user
            if current_user and current_user.is_authenticated and current_user.email:
                recipients.append(current_user.email)
                logger.info(f"Added current user to recipients: {current_user.email}")

            if project:
                # Project responsible (manager)
                if project.responsible and project.responsible.email_alerts and project.responsible.email:
                    if project.responsible.email not in recipients:
                        recipients.append(project.responsible.email)
                # Project resources (team members) - match by name to users
                for resource in project.resources:
                    if resource.name:
                        user = User.query.filter_by(
                            tenant_id=project.tenant_id,
                            full_name=resource.name,
                            active=True
                        ).first()
                        if user and user.email_alerts and user.email and user.email not in recipients:
                            recipients.append(user.email)

            if not recipients:
                return {'success': False, 'error': 'Nenhum destinatário com alertas habilitados'}

            # Configure mail with tenant settings
            if tenant and tenant.mail_server and tenant.mail_username:
                port = tenant.mail_port or 587
                if port == 465:
                    use_ssl, use_tls = True, False
                else:
                    use_ssl, use_tls = False, True

                current_app.config['MAIL_SERVER'] = tenant.mail_server
                current_app.config['MAIL_PORT'] = port
                current_app.config['MAIL_USE_TLS'] = use_tls
                current_app.config['MAIL_USE_SSL'] = use_ssl
                current_app.config['MAIL_USERNAME'] = tenant.mail_username
                current_app.config['MAIL_PASSWORD'] = tenant.mail_password
                current_app.config['MAIL_DEFAULT_SENDER'] = tenant.mail_default_sender or tenant.mail_username

            mail = Mail(current_app)

            # Build email content
            priority_icons = {'critical': '🔴', 'high': '🟠', 'medium': '🟡', 'low': '🟢'}
            icon = priority_icons.get(action.priority.value, '📢')

            html_content = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: #1a237e; color: white; padding: 20px; text-align: center;">
                    <h2>{icon} {action.title}</h2>
                </div>
                <div style="padding: 20px; background: #f5f5f5;">
                    <p><strong>Projeto:</strong> {project.title if project else 'N/A'}</p>
                    <p><strong>Prioridade:</strong> {action.priority.value.upper()}</p>
                    <hr style="border: 1px solid #ddd;">
                    <p>{action.description}</p>
                </div>
                <div style="padding: 10px; text-align: center; color: #666; font-size: 12px;">
                    Orion PMO - Sistema de Gestão de Projetos P&D
                </div>
            </div>
            """

            sent_count = 0
            for recipient in recipients:
                try:
                    msg = Message(
                        subject=f"{icon} {action.title}",
                        recipients=[recipient],
                        html=html_content
                    )
                    mail.send(msg)
                    sent_count += 1
                    logger.info(f"Notification sent to {recipient}")
                except Exception as e:
                    logger.error(f"Failed to send notification to {recipient}: {e}")

            return {
                'success': True,
                'sent_count': sent_count,
                'recipients': recipients,
                'action': 'notification_sent'
            }

        except Exception as e:
            logger.error(f"Error sending notification: {e}")
            return {'success': False, 'error': str(e)}

    def _execute_generate_report(self, action: ActionSuggestion) -> Dict:
        """Generate a report."""
        report_type = action.data.get('report_type', 'general')

        if report_type == 'weekly_status':
            comm_agent = self._agents.get('communication_agent')
            if comm_agent:
                report = comm_agent.generate_weekly_status(action.project_id)
                return {'success': True, 'report': report}

        return {'success': True, 'action': 'report_generation_triggered'}

    def _execute_create_scenario(self, action: ActionSuggestion) -> Dict:
        """Generate alternative scenarios."""
        fin_agent = self._agents.get('financial_agent')
        if fin_agent and action.project_id:
            scenarios = fin_agent.generate_financial_scenarios(action.project_id)
            return {'success': True, 'scenarios': scenarios}

        return {'success': False, 'error': 'Could not generate scenarios'}

    def get_agent_info(self) -> List[Dict]:
        """Get information about all registered agents."""
        info = []
        for name, agent in self._agents.items():
            info.append({
                'name': name,
                'display_name': agent.display_name,
                'description': agent.description,
                'icon': agent.icon,
                'color': agent.color
            })
        return info
