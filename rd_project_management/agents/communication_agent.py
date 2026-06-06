"""
Communication Agent - Generates executive communications.
Outputs: Weekly status, steering committee materials, executive reports, notifications.
"""
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict
from .base import (
    BaseAgent, AgentResult, Insight, ActionSuggestion,
    Severity, HealthStatus, ActionType, health_emoji, severity_emoji
)


class CommunicationAgent(BaseAgent):
    """
    Agente Executivo de Comunicação.
    Generates status reports, executive summaries, and notifications.
    """

    @property
    def name(self) -> str:
        return 'communication_agent'

    @property
    def display_name(self) -> str:
        return 'Agente de Comunicação'

    @property
    def description(self) -> str:
        return 'Gera status report, material para diretoria e notificações'

    @property
    def icon(self) -> str:
        return 'bi-megaphone'

    @property
    def color(self) -> str:
        return 'info'

    def analyze(self, project_id: Optional[int] = None) -> AgentResult:
        self._start_execution()

        insights = []
        actions = []
        metrics = {
            'communication_pending': 0,
            'overdue_updates': 0,
            'stakeholder_alerts': 0
        }

        communication_needs = self._analyze_communication_needs(project_id)
        insights.extend(communication_needs['insights'])
        actions.extend(communication_needs['actions'])
        metrics.update(communication_needs['metrics'])

        overall_status = HealthStatus.HEALTHY
        if metrics['overdue_updates'] > 0:
            overall_status = HealthStatus.ATTENTION

        summary = self._generate_summary(metrics, overall_status)

        return self.create_result(
            success=True,
            insights=insights,
            actions=actions,
            summary=summary,
            health_status=overall_status,
            metrics=metrics
        )

    def _analyze_communication_needs(self, project_id: Optional[int] = None) -> Dict:
        """Identify communication needs."""
        from models import Project, Milestone

        insights = []
        actions = []
        metrics = {
            'communication_pending': 0,
            'overdue_updates': 0,
            'stakeholder_alerts': 0
        }

        query = Project.query.filter_by(tenant_id=self.tenant_id)
        if project_id:
            query = query.filter_by(id=project_id)
        else:
            query = query.filter(Project.status.in_(['Em Andamento', 'Planejamento']))

        projects = query.all()
        today = date.today()

        for project in projects:
            last_update = project.updated_at.date() if project.updated_at else None
            if last_update and (today - last_update).days > 7:
                metrics['overdue_updates'] += 1
                insights.append(self.create_insight(
                    title=f'Projeto sem atualização há {(today - last_update).days} dias',
                    description=f'{project.title} não foi atualizado recentemente.',
                    severity=Severity.MEDIUM,
                    category='update_needed',
                    project_id=project.id,
                    project_name=project.title
                ))

            # Get milestones completed recently (based on end_date within last 7 days)
            recent_milestones = Milestone.query.filter_by(
                project_id=project.id,
                status='Concluído'
            ).filter(
                Milestone.end_date >= today - timedelta(days=7)
            ).all()

            if recent_milestones:
                actions.append(self.suggest_action(
                    action_type=ActionType.SEND_NOTIFICATION,
                    title=f'Comunicar marco(s) atingido(s)',
                    description=f'{len(recent_milestones)} marco(s) concluído(s) em {project.title}.',
                    priority=Severity.LOW,
                    project_id=project.id,
                    data={'milestone_ids': [m.id for m in recent_milestones]}
                ))

        if today.weekday() == 0:
            actions.append(self.suggest_action(
                action_type=ActionType.GENERATE_REPORT,
                title='Gerar Status Report Semanal',
                description='Segunda-feira - dia de envio do status report semanal.',
                priority=Severity.MEDIUM,
                data={'report_type': 'weekly_status'}
            ))

        return {
            'insights': insights,
            'actions': actions,
            'metrics': metrics
        }

    def generate_weekly_status(self, project_id: Optional[int] = None) -> str:
        """Generate weekly status report content."""
        from models import Project, Milestone, Expense, Risk

        today = date.today()
        week_start = today - timedelta(days=today.weekday())

        query = Project.query.filter_by(tenant_id=self.tenant_id)
        if project_id:
            query = query.filter_by(id=project_id)
        else:
            query = query.filter(Project.status.in_(['Em Andamento']))

        projects = query.all()

        report = f"""
================================================================================
                    STATUS REPORT SEMANAL
                    Semana de {week_start.strftime('%d/%m/%Y')}
================================================================================

RESUMO EXECUTIVO
--------------------------------------------------------------------------------
"""
        total = len(projects)
        healthy = 0
        attention = 0
        critical = 0

        for project in projects:
            status = self._get_project_health_status(project)
            if status == 'healthy':
                healthy += 1
            elif status == 'attention':
                attention += 1
            else:
                critical += 1

        report += f"""
🟢 Saudáveis: {healthy}
🟡 Atenção: {attention}
🔴 Críticos: {critical}
Total de Projetos Ativos: {total}

"""
        report += """
DETALHAMENTO POR PROJETO
--------------------------------------------------------------------------------
"""

        for project in projects:
            milestones = Milestone.query.filter_by(project_id=project.id).all()
            completed = sum(1 for m in milestones if m.status == 'Concluído')
            total_m = len(milestones)
            progress = (completed / total_m * 100) if total_m > 0 else 0

            expenses = Expense.query.filter_by(project_id=project.id).all()
            spent = sum(e.amount for e in expenses)
            budget = project.budget or 0
            budget_pct = (spent / budget * 100) if budget > 0 else 0

            status_emoji = self._get_project_health_emoji(project)

            report += f"""
{status_emoji} {project.title} ({project.code})
   Progresso: {progress:.0f}% ({completed}/{total_m} marcos)
   Orçamento: R$ {spent:,.2f} / R$ {budget:,.2f} ({budget_pct:.0f}%)
   Status: {project.status}
"""
            overdue = [m for m in milestones if m.status != 'Concluído' and m.end_date and m.end_date < today]
            if overdue:
                report += f"   ⚠️ Atrasos: {len(overdue)} marco(s)\n"

            risks = Risk.query.filter_by(project_id=project.id).filter(
                Risk.status.notin_(['Fechado', 'Mitigado'])
            ).all()
            high_risks = [r for r in risks if r.risk_score >= 12]
            if high_risks:
                report += f"   ⚠️ Riscos Altos: {len(high_risks)}\n"

        report += """
--------------------------------------------------------------------------------
                    Relatório gerado automaticamente pelo Orion PMO
================================================================================
"""
        return report

    def generate_executive_summary(self, agent_results: List[AgentResult]) -> str:
        """Generate executive summary from multiple agent results."""
        today = datetime.now()

        summary = f"""
================================================================================
                    BRIEFING EXECUTIVO DIÁRIO
                    {today.strftime('%d/%m/%Y %H:%M')}
================================================================================

"""
        critical_count = 0
        high_count = 0
        attention_items = []

        for result in agent_results:
            critical_count += result.critical_count
            high_count += result.high_count

            if result.health_status == HealthStatus.CRITICAL:
                attention_items.append(f"🔴 {result.agent_name}: {result.summary}")
            elif result.health_status == HealthStatus.ATTENTION:
                attention_items.append(f"🟡 {result.agent_name}: {result.summary}")

        if critical_count == 0 and high_count == 0:
            summary += "✅ SITUAÇÃO GERAL: Operações normais. Nenhum alerta crítico.\n\n"
        else:
            summary += f"⚠️ SITUAÇÃO GERAL: {critical_count} alerta(s) crítico(s), {high_count} de alta prioridade.\n\n"

        if attention_items:
            summary += "ITENS QUE REQUEREM ATENÇÃO:\n"
            summary += "-" * 60 + "\n"
            for item in attention_items:
                summary += f"{item}\n"
            summary += "\n"

        summary += "RESUMO POR ÁREA:\n"
        summary += "-" * 60 + "\n"
        for result in agent_results:
            emoji = health_emoji(result.health_status) if result.health_status else '⚪'
            summary += f"{emoji} {result.agent_name}: {result.summary}\n"

        all_actions = []
        for result in agent_results:
            all_actions.extend(result.actions)

        critical_actions = [a for a in all_actions if a.priority in [Severity.CRITICAL, Severity.HIGH]]
        if critical_actions:
            summary += f"\nAÇÕES RECOMENDADAS ({len(critical_actions)}):\n"
            summary += "-" * 60 + "\n"
            for action in critical_actions[:5]:
                summary += f"• {action.title}\n  {action.description}\n\n"

        summary += """
--------------------------------------------------------------------------------
                    Orion Autonomous PMO - Daily Executive AI
================================================================================
"""
        return summary

    def _get_project_health_status(self, project) -> str:
        """Determine project health status."""
        from models import Milestone, Expense

        today = date.today()

        milestones = Milestone.query.filter_by(project_id=project.id).all()
        overdue = [m for m in milestones if m.status != 'Concluído' and m.end_date and m.end_date < today]

        expenses = Expense.query.filter_by(project_id=project.id).all()
        spent = sum(e.amount for e in expenses)
        budget = project.budget or 0

        if len(overdue) > 2 or (budget > 0 and spent > budget):
            return 'critical'
        elif len(overdue) > 0 or (budget > 0 and spent > budget * 0.9):
            return 'attention'
        return 'healthy'

    def _get_project_health_emoji(self, project) -> str:
        """Get health emoji for project."""
        status = self._get_project_health_status(project)
        mapping = {'healthy': '🟢', 'attention': '🟡', 'critical': '🔴'}
        return mapping.get(status, '⚪')

    def _generate_summary(self, metrics: Dict, status: HealthStatus) -> str:
        """Generate agent summary."""
        overdue = metrics['overdue_updates']
        pending = metrics['communication_pending']

        if overdue > 0:
            return f"🟡 {overdue} projeto(s) sem atualização recente."
        else:
            return f"🟢 Comunicações em dia."
