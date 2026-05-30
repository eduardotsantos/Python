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
            'generated_at': self.generated_at.isoformat()
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
        summary = self._generate_executive_summary(results, overall_status, user_name)

        briefing = DailyBriefing(
            date=date.today(),
            tenant_id=self.tenant_id,
            overall_status=overall_status,
            summary=summary,
            agent_results=results,
            priority_items=priority_items,
            recommended_actions=recommended_actions[:10],
            metrics=metrics
        )

        return briefing

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
        user_name: str
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
        """Send notification (generates content for various channels)."""
        notification = {
            'title': action.title,
            'message': action.description,
            'project_id': action.project_id,
            'channels': ['email', 'in_app'],
            'priority': action.priority.value
        }
        return {'success': True, 'notification': notification, 'action': 'notification_queued'}

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
