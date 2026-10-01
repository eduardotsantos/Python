"""
Quality Agent - Monitors quality indicators.
Analyzes: Pending items, bugs, non-conformities, rework.
"""
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict
from .base import (
    BaseAgent, AgentResult, Insight, ActionSuggestion,
    Severity, HealthStatus, ActionType
)


class QualityAgent(BaseAgent):
    """
    Agente de Qualidade.
    Monitors quality metrics and generates quality index.
    """

    @property
    def name(self) -> str:
        return 'quality_agent'

    @property
    def display_name(self) -> str:
        return 'Agente de Qualidade'

    @property
    def description(self) -> str:
        return 'Monitora pendências, bugs, não conformidades e retrabalho'

    @property
    def icon(self) -> str:
        return 'bi-patch-check'

    @property
    def color(self) -> str:
        return 'warning'

    def analyze(self, project_id: Optional[int] = None) -> AgentResult:
        self._start_execution()

        from models import Project, Bug, NonConformity, PendingItem, CorrectiveAction

        insights = []
        actions = []
        metrics = {
            'total_bugs': 0,
            'open_bugs': 0,
            'critical_bugs': 0,
            'total_nc': 0,
            'open_nc': 0,
            'total_pending': 0,
            'overdue_pending': 0,
            'resolution_rate': 0,
            'quality_index': 100,
            'by_project': []
        }

        query = Project.query.filter_by(tenant_id=self.tenant_id)
        if project_id:
            query = query.filter_by(id=project_id)
        else:
            query = query.filter(Project.status.in_(['Em Andamento', 'Planejamento']))

        projects = query.all()

        for project in projects:
            project_quality = self._analyze_project_quality(project)
            metrics['by_project'].append(project_quality)

            metrics['total_bugs'] += project_quality['bugs']['total']
            metrics['open_bugs'] += project_quality['bugs']['open']
            metrics['critical_bugs'] += project_quality['bugs']['critical']
            metrics['total_nc'] += project_quality['nc']['total']
            metrics['open_nc'] += project_quality['nc']['open']
            metrics['total_pending'] += project_quality['pending']['total']
            metrics['overdue_pending'] += project_quality['pending']['overdue']

            insights.extend(project_quality['insights'])
            actions.extend(project_quality['actions'])

        metrics['quality_index'] = self._calculate_quality_index(metrics)
        if metrics['total_bugs'] > 0:
            closed = metrics['total_bugs'] - metrics['open_bugs']
            metrics['resolution_rate'] = (closed / metrics['total_bugs']) * 100

        portfolio_insights = self._analyze_portfolio_quality(metrics)
        insights.extend(portfolio_insights)

        overall_status = HealthStatus.HEALTHY
        if metrics['quality_index'] < 60 or metrics['critical_bugs'] > 0:
            overall_status = HealthStatus.CRITICAL
        elif metrics['quality_index'] < 80:
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

    def _analyze_project_quality(self, project) -> Dict:
        """Analyze quality metrics for a single project."""
        from models import Bug, NonConformity, PendingItem

        insights = []
        actions = []
        today = date.today()

        bugs = Bug.query.filter_by(project_id=project.id).all()
        open_bugs = [b for b in bugs if b.status not in ['Resolvido', 'Fechado']]
        critical_bugs = [b for b in open_bugs if b.severity == 'Crítica']

        ncs = NonConformity.query.filter_by(project_id=project.id).all()
        open_ncs = [nc for nc in ncs if nc.status != 'Fechada']

        pending = PendingItem.query.filter_by(project_id=project.id).all()
        open_pending = [p for p in pending if p.status not in ['Resolvida', 'Cancelada']]
        overdue_pending = [p for p in open_pending if p.due_date and p.due_date < today]

        if critical_bugs:
            insights.append(self.create_insight(
                title=f'{len(critical_bugs)} bug(s) crítico(s) aberto(s)',
                description=f'Bugs de severidade crítica sem resolução no projeto {project.title}.',
                severity=Severity.CRITICAL,
                category='bugs',
                project_id=project.id,
                project_name=project.title,
                metric_name='critical_bugs',
                metric_value=len(critical_bugs),
                recommendation='Priorizar correção imediata dos bugs críticos.'
            ))

            for bug in critical_bugs[:2]:
                actions.append(self.suggest_action(
                    action_type=ActionType.ESCALATE,
                    title=f'Escalar bug crítico: {bug.title[:40]}',
                    description=f'Bug crítico requer atenção imediata.',
                    priority=Severity.CRITICAL,
                    project_id=project.id,
                    data={'bug_id': bug.id}
                ))

        if len(open_ncs) > 5:
            insights.append(self.create_insight(
                title=f'{len(open_ncs)} não conformidades abertas',
                description=f'Alto volume de NCs sem tratamento em {project.title}.',
                severity=Severity.HIGH if len(open_ncs) > 10 else Severity.MEDIUM,
                category='nc',
                project_id=project.id,
                project_name=project.title,
                metric_name='open_nc',
                metric_value=len(open_ncs)
            ))

        if overdue_pending:
            max_overdue = max((today - p.due_date).days for p in overdue_pending)
            severity = Severity.HIGH if max_overdue > 14 else Severity.MEDIUM

            insights.append(self.create_insight(
                title=f'{len(overdue_pending)} pendência(s) vencida(s)',
                description=f'Pendências vencidas há até {max_overdue} dias em {project.title}.',
                severity=severity,
                category='pending',
                project_id=project.id,
                project_name=project.title,
                metric_name='overdue_pending',
                metric_value=len(overdue_pending)
            ))

            actions.append(self.suggest_action(
                action_type=ActionType.SEND_NOTIFICATION,
                title='Enviar cobrança de pendências',
                description=f'{len(overdue_pending)} pendências vencidas precisam de acompanhamento.',
                priority=severity,
                project_id=project.id,
                data={'pending_ids': [p.id for p in overdue_pending]}
            ))

        return {
            'project_id': project.id,
            'project_name': project.title,
            'bugs': {
                'total': len(bugs),
                'open': len(open_bugs),
                'critical': len(critical_bugs)
            },
            'nc': {
                'total': len(ncs),
                'open': len(open_ncs)
            },
            'pending': {
                'total': len(pending),
                'open': len(open_pending),
                'overdue': len(overdue_pending)
            },
            'insights': insights,
            'actions': actions
        }

    def _calculate_quality_index(self, metrics: Dict) -> float:
        """Calculate overall quality index (0-100)."""
        index = 100

        index -= metrics['critical_bugs'] * 15
        index -= min(20, metrics['open_bugs'] * 2)
        index -= min(15, metrics['open_nc'] * 3)
        index -= min(10, metrics['overdue_pending'])

        return max(0, min(100, index))

    def _analyze_portfolio_quality(self, metrics: Dict) -> List[Insight]:
        """Analyze portfolio-level quality trends."""
        insights = []

        qi = metrics['quality_index']
        if qi >= 80:
            insights.append(self.create_insight(
                title=f'Índice de Qualidade: {qi:.0f}/100',
                description='Portfolio com bom nível de qualidade.',
                severity=Severity.INFO,
                category='quality_index'
            ))
        elif qi >= 60:
            insights.append(self.create_insight(
                title=f'Índice de Qualidade: {qi:.0f}/100',
                description='Portfolio requer atenção em métricas de qualidade.',
                severity=Severity.MEDIUM,
                category='quality_index',
                recommendation='Focar na resolução de bugs e pendências abertas.'
            ))
        else:
            insights.append(self.create_insight(
                title=f'Índice de Qualidade Crítico: {qi:.0f}/100',
                description='Qualidade do portfolio abaixo do aceitável.',
                severity=Severity.CRITICAL,
                category='quality_index',
                recommendation='Ação urgente necessária para recuperar qualidade.'
            ))

        resolution_rate = metrics.get('resolution_rate', 0)
        if resolution_rate > 0 and resolution_rate < 50:
            insights.append(self.create_insight(
                title=f'Taxa de resolução baixa: {resolution_rate:.0f}%',
                description='Menos da metade dos bugs registrados foram resolvidos.',
                severity=Severity.MEDIUM,
                category='resolution',
                recommendation='Revisar processo de triagem e priorização de bugs.'
            ))

        return insights

    def _generate_summary(self, metrics: Dict, status: HealthStatus) -> str:
        """Generate executive summary."""
        qi = metrics['quality_index']
        bugs = metrics['open_bugs']
        critical = metrics['critical_bugs']
        pending = metrics['overdue_pending']

        if status == HealthStatus.CRITICAL:
            return f"🔴 Qualidade crítica (índice {qi:.0f}). {critical} bug(s) crítico(s), {pending} pendência(s) vencida(s)."
        elif status == HealthStatus.ATTENTION:
            return f"🟡 Qualidade em atenção (índice {qi:.0f}). {bugs} bug(s) aberto(s), {pending} pendência(s) vencida(s)."
        else:
            return f"🟢 Qualidade saudável (índice {qi:.0f}/100). {bugs} bug(s) em tratamento."
