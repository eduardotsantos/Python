"""
Project Health Agent - Monitors overall project health.
Analyzes: Schedule, Budget, Scope, Quality, Dependencies.
"""
from datetime import datetime, date, timedelta
from typing import Optional, List
from .base import (
    BaseAgent, AgentResult, Insight, ActionSuggestion,
    Severity, HealthStatus, ActionType
)


class ProjectHealthAgent(BaseAgent):
    """
    Agente de Saúde do Projeto.
    Monitors overall health indicators and generates alerts.
    """

    @property
    def name(self) -> str:
        return 'health_agent'

    @property
    def display_name(self) -> str:
        return 'Agente de Saúde do Projeto'

    @property
    def description(self) -> str:
        return 'Monitora cronograma, orçamento, escopo, qualidade e dependências'

    @property
    def icon(self) -> str:
        return 'bi-heart-pulse'

    @property
    def color(self) -> str:
        return 'success'

    def analyze(self, project_id: Optional[int] = None) -> AgentResult:
        self._start_execution()

        from models import Project, Milestone, Expense, Risk, PendingItem, NonConformity, Bug

        insights = []
        actions = []
        metrics = {
            'total_projects': 0,
            'healthy': 0,
            'attention': 0,
            'critical': 0,
            'projects_analyzed': []
        }

        query = Project.query.filter_by(tenant_id=self.tenant_id)
        if project_id:
            query = query.filter_by(id=project_id)
        else:
            query = query.filter(Project.status.in_(['Em Andamento', 'Planejamento']))

        projects = query.all()
        metrics['total_projects'] = len(projects)

        for project in projects:
            project_health = self._analyze_project_health(project)
            metrics['projects_analyzed'].append(project_health)

            if project_health['status'] == HealthStatus.CRITICAL:
                metrics['critical'] += 1
            elif project_health['status'] == HealthStatus.ATTENTION:
                metrics['attention'] += 1
            else:
                metrics['healthy'] += 1

            insights.extend(project_health['insights'])
            actions.extend(project_health['actions'])

        overall_status = HealthStatus.HEALTHY
        if metrics['critical'] > 0:
            overall_status = HealthStatus.CRITICAL
        elif metrics['attention'] > 0:
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

    def _analyze_project_health(self, project) -> dict:
        """Analyze health of a single project."""
        from models import Milestone, Expense, Risk, PendingItem, NonConformity, Bug

        insights = []
        actions = []
        health_scores = []

        schedule_health = self._check_schedule_health(project)
        health_scores.append(schedule_health['score'])
        insights.extend(schedule_health['insights'])
        actions.extend(schedule_health['actions'])

        budget_health = self._check_budget_health(project)
        health_scores.append(budget_health['score'])
        insights.extend(budget_health['insights'])
        actions.extend(budget_health['actions'])

        quality_health = self._check_quality_health(project)
        health_scores.append(quality_health['score'])
        insights.extend(quality_health['insights'])

        risk_health = self._check_risk_health(project)
        health_scores.append(risk_health['score'])
        insights.extend(risk_health['insights'])
        actions.extend(risk_health['actions'])

        avg_score = sum(health_scores) / len(health_scores) if health_scores else 100

        if avg_score >= 80:
            status = HealthStatus.HEALTHY
        elif avg_score >= 50:
            status = HealthStatus.ATTENTION
        else:
            status = HealthStatus.CRITICAL

        return {
            'project_id': project.id,
            'project_name': project.title,
            'status': status,
            'score': avg_score,
            'insights': insights,
            'actions': actions
        }

    def _check_schedule_health(self, project) -> dict:
        """Check schedule/timeline health."""
        from models import Milestone

        insights = []
        actions = []
        score = 100

        milestones = Milestone.query.filter_by(project_id=project.id).all()
        today = date.today()

        overdue_milestones = []
        upcoming_critical = []

        for m in milestones:
            if m.status != 'Concluído' and m.end_date:
                if m.end_date < today:
                    days_late = (today - m.end_date).days
                    overdue_milestones.append((m, days_late))
                elif m.end_date <= today + timedelta(days=7):
                    upcoming_critical.append(m)

        if overdue_milestones:
            max_late = max(days for _, days in overdue_milestones)
            score -= min(50, max_late * 2)

            worst = max(overdue_milestones, key=lambda x: x[1])
            severity = Severity.CRITICAL if worst[1] > 14 else Severity.HIGH

            insights.append(self.create_insight(
                title=f'Atraso no cronograma: {worst[1]} dias',
                description=f'Marco "{worst[0].title}" está atrasado {worst[1]} dias. Total de {len(overdue_milestones)} marcos atrasados.',
                severity=severity,
                category='schedule',
                project_id=project.id,
                project_name=project.title,
                metric_name='dias_atraso',
                metric_value=worst[1],
                recommendation='Revisar dependências e realocar recursos para recuperar o cronograma.'
            ))

            actions.append(self.suggest_action(
                action_type=ActionType.SCHEDULE_MEETING,
                title='Agendar reunião de recovery',
                description=f'Reunião para discutir recuperação do cronograma do projeto {project.title}',
                priority=severity,
                project_id=project.id,
                data={'milestone_id': worst[0].id, 'days_late': worst[1]}
            ))

        if upcoming_critical:
            score -= len(upcoming_critical) * 5
            insights.append(self.create_insight(
                title=f'{len(upcoming_critical)} marcos críticos próximos',
                description=f'Existem {len(upcoming_critical)} marcos vencendo nos próximos 7 dias.',
                severity=Severity.MEDIUM,
                category='schedule',
                project_id=project.id,
                project_name=project.title
            ))

        if project.end_date and project.end_date < today and project.status != 'Concluído':
            days_over = (today - project.end_date).days
            score -= 30
            insights.append(self.create_insight(
                title=f'Projeto ultrapassou data de término',
                description=f'O projeto deveria ter terminado há {days_over} dias.',
                severity=Severity.CRITICAL,
                category='schedule',
                project_id=project.id,
                project_name=project.title,
                metric_value=days_over
            ))

        return {'score': max(0, score), 'insights': insights, 'actions': actions}

    def _check_budget_health(self, project) -> dict:
        """Check budget/financial health."""
        from models import Expense, Milestone

        insights = []
        actions = []
        score = 100

        expenses = Expense.query.filter_by(project_id=project.id).all()
        total_spent = sum(e.amount for e in expenses)
        budget = project.budget or 0

        if budget > 0:
            consumption_pct = (total_spent / budget) * 100

            milestones = Milestone.query.filter_by(project_id=project.id).all()
            completed = sum(1 for m in milestones if m.status == 'Concluído')
            total_milestones = len(milestones)
            progress_pct = (completed / total_milestones * 100) if total_milestones > 0 else 0

            if consumption_pct > 90 and progress_pct < 80:
                score -= 40
                insights.append(self.create_insight(
                    title='Risco de estouro de orçamento',
                    description=f'Consumiu {consumption_pct:.0f}% do orçamento com apenas {progress_pct:.0f}% das entregas.',
                    severity=Severity.CRITICAL,
                    category='budget',
                    project_id=project.id,
                    project_name=project.title,
                    metric_name='consumo_orcamento',
                    metric_value=consumption_pct,
                    recommendation='Revisar escopo ou solicitar aporte adicional.'
                ))

                actions.append(self.suggest_action(
                    action_type=ActionType.CREATE_SCENARIO,
                    title='Gerar cenários alternativos',
                    description='Criar 3 cenários para recuperação do orçamento',
                    priority=Severity.HIGH,
                    project_id=project.id,
                    data={'consumption': consumption_pct, 'progress': progress_pct}
                ))

            elif consumption_pct > progress_pct + 20:
                score -= 20
                insights.append(self.create_insight(
                    title='Desvio orçamentário',
                    description=f'Consumo ({consumption_pct:.0f}%) acima do progresso ({progress_pct:.0f}%).',
                    severity=Severity.HIGH,
                    category='budget',
                    project_id=project.id,
                    project_name=project.title,
                    metric_name='desvio_orcamentario',
                    metric_value=consumption_pct - progress_pct
                ))

        return {'score': max(0, score), 'insights': insights, 'actions': actions}

    def _check_quality_health(self, project) -> dict:
        """Check quality indicators."""
        from models import Bug, NonConformity, PendingItem

        insights = []
        score = 100

        open_bugs = Bug.query.filter_by(
            project_id=project.id
        ).filter(Bug.status.notin_(['Resolvido', 'Fechado'])).count()

        critical_bugs = Bug.query.filter_by(
            project_id=project.id,
            severity='Crítica'
        ).filter(Bug.status.notin_(['Resolvido', 'Fechado'])).count()

        open_nc = NonConformity.query.filter_by(
            project_id=project.id
        ).filter(NonConformity.status != 'Fechada').count()

        overdue_pending = PendingItem.query.filter_by(
            project_id=project.id
        ).filter(
            PendingItem.status.notin_(['Resolvida', 'Cancelada']),
            PendingItem.due_date < date.today()
        ).count()

        if critical_bugs > 0:
            score -= critical_bugs * 15
            insights.append(self.create_insight(
                title=f'{critical_bugs} bugs críticos abertos',
                description=f'Existem {critical_bugs} bugs de severidade crítica não resolvidos.',
                severity=Severity.CRITICAL,
                category='quality',
                project_id=project.id,
                project_name=project.title,
                metric_name='bugs_criticos',
                metric_value=critical_bugs
            ))

        if open_nc > 3:
            score -= open_nc * 5
            insights.append(self.create_insight(
                title=f'{open_nc} não conformidades abertas',
                description=f'Alto número de não conformidades sem tratamento.',
                severity=Severity.HIGH if open_nc > 5 else Severity.MEDIUM,
                category='quality',
                project_id=project.id,
                project_name=project.title
            ))

        if overdue_pending > 5:
            score -= 10
            insights.append(self.create_insight(
                title=f'{overdue_pending} pendências vencidas',
                description=f'Existem {overdue_pending} pendências vencidas sem resolução.',
                severity=Severity.MEDIUM,
                category='quality',
                project_id=project.id,
                project_name=project.title
            ))

        return {'score': max(0, score), 'insights': insights, 'actions': []}

    def _check_risk_health(self, project) -> dict:
        """Check risk indicators."""
        from models import Risk

        insights = []
        actions = []
        score = 100

        open_risks = Risk.query.filter_by(
            project_id=project.id
        ).filter(Risk.status.notin_(['Fechado', 'Mitigado'])).all()

        high_risks = [r for r in open_risks if r.risk_score >= 12]
        risks_no_plan = [r for r in open_risks if not r.mitigation_plan]

        if high_risks:
            score -= len(high_risks) * 10
            worst = max(high_risks, key=lambda r: r.risk_score)
            insights.append(self.create_insight(
                title=f'{len(high_risks)} riscos de alto impacto',
                description=f'Risco mais crítico: "{worst.title}" (score {worst.risk_score}).',
                severity=Severity.HIGH,
                category='risk',
                project_id=project.id,
                project_name=project.title,
                metric_name='riscos_alto_impacto',
                metric_value=len(high_risks)
            ))

        if risks_no_plan:
            score -= len(risks_no_plan) * 5
            insights.append(self.create_insight(
                title=f'{len(risks_no_plan)} riscos sem plano de mitigação',
                description='Riscos identificados sem plano de tratamento definido.',
                severity=Severity.MEDIUM,
                category='risk',
                project_id=project.id,
                project_name=project.title
            ))

            for risk in risks_no_plan[:3]:
                actions.append(self.suggest_action(
                    action_type=ActionType.CREATE_ACTION,
                    title=f'Criar plano para risco: {risk.title[:40]}',
                    description='Definir plano de mitigação para o risco identificado',
                    priority=Severity.MEDIUM,
                    project_id=project.id,
                    data={'risk_id': risk.id}
                ))

        return {'score': max(0, score), 'insights': insights, 'actions': actions}

    def _generate_summary(self, metrics: dict, status: HealthStatus) -> str:
        """Generate executive summary."""
        total = metrics['total_projects']
        healthy = metrics['healthy']
        attention = metrics['attention']
        critical = metrics['critical']

        if status == HealthStatus.HEALTHY:
            return f"✅ Todos os {total} projetos estão saudáveis."
        elif status == HealthStatus.CRITICAL:
            return f"🔴 {critical} projeto(s) crítico(s) de {total}. 🟡 {attention} em atenção. 🟢 {healthy} saudável(is)."
        else:
            return f"🟡 {attention} projeto(s) requer(em) atenção de {total}. 🟢 {healthy} saudável(is)."
