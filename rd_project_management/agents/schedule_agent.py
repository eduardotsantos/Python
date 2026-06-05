"""
Schedule Agent - Analyzes project schedules and timelines.
Monitors: Critical path, dependencies, delays, milestones.
"""
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict
from .base import (
    BaseAgent, AgentResult, Insight, ActionSuggestion,
    Severity, HealthStatus, ActionType
)


class ScheduleAgent(BaseAgent):
    """
    Agente de Cronograma.
    Analyzes schedules, dependencies, critical path, and suggests optimizations.
    """

    @property
    def name(self) -> str:
        return 'schedule_agent'

    @property
    def display_name(self) -> str:
        return 'Agente de Cronograma'

    @property
    def description(self) -> str:
        return 'Analisa caminho crítico, dependências, atrasos e marcos'

    @property
    def icon(self) -> str:
        return 'bi-calendar-check'

    @property
    def color(self) -> str:
        return 'info'

    def analyze(self, project_id: Optional[int] = None) -> AgentResult:
        self._start_execution()

        from models import Project, Milestone

        insights = []
        actions = []
        metrics = {
            'total_milestones': 0,
            'completed': 0,
            'overdue': 0,
            'upcoming_7_days': 0,
            'upcoming_30_days': 0,
            'no_date': 0,
            'avg_delay_days': 0,
            'projects_delayed': 0,
            'critical_path': []
        }

        query = Project.query.filter_by(tenant_id=self.tenant_id)
        if project_id:
            query = query.filter_by(id=project_id)
        else:
            query = query.filter(Project.status.in_(['Em Andamento', 'Planejamento']))

        projects = query.all()
        today = date.today()

        all_delays = []
        for project in projects:
            project_analysis = self._analyze_project_schedule(project)

            metrics['total_milestones'] += project_analysis['total']
            metrics['completed'] += project_analysis['completed']
            metrics['overdue'] += project_analysis['overdue']
            metrics['upcoming_7_days'] += project_analysis['upcoming_7']
            metrics['upcoming_30_days'] += project_analysis['upcoming_30']
            metrics['no_date'] += project_analysis['no_date']

            if project_analysis['delays']:
                all_delays.extend(project_analysis['delays'])
                metrics['projects_delayed'] += 1

            insights.extend(project_analysis['insights'])
            actions.extend(project_analysis['actions'])

        if all_delays:
            metrics['avg_delay_days'] = sum(all_delays) / len(all_delays)
            metrics['max_delay_days'] = max(all_delays)

        portfolio_insights = self._analyze_portfolio_schedule(metrics, projects)
        insights.extend(portfolio_insights)

        overall_status = HealthStatus.HEALTHY
        if metrics['overdue'] > 0:
            if metrics.get('max_delay_days', 0) > 14:
                overall_status = HealthStatus.CRITICAL
            else:
                overall_status = HealthStatus.ATTENTION
        elif metrics['upcoming_7_days'] > 5:
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

    def _analyze_project_schedule(self, project) -> Dict:
        """Analyze schedule of a single project."""
        from models import Milestone

        insights = []
        actions = []
        today = date.today()

        milestones = Milestone.query.filter_by(project_id=project.id).order_by(Milestone.end_date).all()

        total = len(milestones)
        completed = sum(1 for m in milestones if m.status == 'Concluído')
        overdue = 0
        upcoming_7 = 0
        upcoming_30 = 0
        no_date = 0
        delays = []

        overdue_milestones = []
        for m in milestones:
            if not m.end_date:
                no_date += 1
                continue

            if m.status != 'Concluído':
                if m.end_date < today:
                    overdue += 1
                    days_late = (today - m.end_date).days
                    delays.append(days_late)
                    overdue_milestones.append((m, days_late))
                elif m.end_date <= today + timedelta(days=7):
                    upcoming_7 += 1
                elif m.end_date <= today + timedelta(days=30):
                    upcoming_30 += 1

        if overdue_milestones:
            worst = max(overdue_milestones, key=lambda x: x[1])
            severity = Severity.CRITICAL if worst[1] > 14 else Severity.HIGH

            insights.append(self.create_insight(
                title=f'{overdue} marco(s) atrasado(s)',
                description=f'Maior atraso: "{worst[0].title}" ({worst[1]} dias). Projeto: {project.title}',
                severity=severity,
                category='overdue',
                project_id=project.id,
                project_name=project.title,
                metric_name='max_delay',
                metric_value=worst[1],
                recommendation='Revisar dependências e considerar compressão de cronograma.'
            ))

            if worst[1] > 7:
                actions.append(self.suggest_action(
                    action_type=ActionType.SCHEDULE_MEETING,
                    title='Reunião de recovery',
                    description=f'Discutir recuperação do cronograma do projeto {project.title}',
                    priority=severity,
                    project_id=project.id,
                    data={'milestone_id': worst[0].id, 'days_late': worst[1]}
                ))

                actions.append(self.suggest_action(
                    action_type=ActionType.REPLAN_SCHEDULE,
                    title='Replanejamento de cronograma',
                    description=f'Gerar proposta de replanejamento para {project.title}',
                    priority=Severity.HIGH,
                    project_id=project.id
                ))

        if upcoming_7 >= 3:
            insights.append(self.create_insight(
                title=f'{upcoming_7} marcos críticos esta semana',
                description=f'{upcoming_7} entregas previstas nos próximos 7 dias para {project.title}.',
                severity=Severity.MEDIUM,
                category='upcoming',
                project_id=project.id,
                project_name=project.title
            ))

        deps = self._analyze_dependencies(milestones)
        if deps['blocked']:
            insights.append(self.create_insight(
                title=f'{len(deps["blocked"])} marcos bloqueados',
                description=f'Marcos aguardando conclusão de predecessores atrasados.',
                severity=Severity.HIGH,
                category='dependencies',
                project_id=project.id,
                project_name=project.title
            ))

        return {
            'project_id': project.id,
            'project_name': project.title,
            'total': total,
            'completed': completed,
            'overdue': overdue,
            'upcoming_7': upcoming_7,
            'upcoming_30': upcoming_30,
            'no_date': no_date,
            'delays': delays,
            'insights': insights,
            'actions': actions
        }

    def _analyze_dependencies(self, milestones: list) -> Dict:
        """Analyze milestone dependencies."""
        blocked = []
        critical_chain = []

        milestone_dict = {m.id: m for m in milestones}

        for m in milestones:
            if m.predecessor_id and m.status != 'Concluído':
                predecessor = milestone_dict.get(m.predecessor_id)
                if predecessor and predecessor.status != 'Concluído':
                    if predecessor.end_date and predecessor.end_date < date.today():
                        blocked.append({
                            'milestone': m,
                            'blocked_by': predecessor
                        })

        return {'blocked': blocked, 'critical_chain': critical_chain}

    def _analyze_portfolio_schedule(self, metrics: Dict, projects: list) -> List[Insight]:
        """Analyze portfolio-level schedule health."""
        insights = []

        if metrics['projects_delayed'] > 0:
            total_projects = len(projects)
            pct_delayed = (metrics['projects_delayed'] / total_projects * 100) if total_projects > 0 else 0

            if pct_delayed > 50:
                insights.append(self.create_insight(
                    title=f'{pct_delayed:.0f}% dos projetos atrasados',
                    description=f'{metrics["projects_delayed"]} de {total_projects} projetos com marcos atrasados.',
                    severity=Severity.CRITICAL,
                    category='portfolio',
                    recommendation='Revisar capacidade de entrega e priorização do portfolio.'
                ))

        if metrics['no_date'] > metrics['total_milestones'] * 0.2:
            insights.append(self.create_insight(
                title='Marcos sem data definida',
                description=f'{metrics["no_date"]} marcos ({metrics["no_date"]/metrics["total_milestones"]*100:.0f}%) sem data de entrega.',
                severity=Severity.MEDIUM,
                category='planning',
                recommendation='Definir datas para todos os marcos do cronograma.'
            ))

        return insights

    def _generate_summary(self, metrics: Dict, status: HealthStatus) -> str:
        """Generate executive summary."""
        total = metrics['total_milestones']
        completed = metrics['completed']
        overdue = metrics['overdue']
        upcoming = metrics['upcoming_7_days']

        progress = (completed / total * 100) if total > 0 else 0

        if status == HealthStatus.CRITICAL:
            return f"🔴 {overdue} marco(s) atrasado(s) (máx {metrics.get('max_delay_days', 0):.0f} dias). Progresso: {progress:.0f}%."
        elif status == HealthStatus.ATTENTION:
            return f"🟡 {overdue} atraso(s), {upcoming} entregas esta semana. Progresso: {progress:.0f}%."
        else:
            return f"🟢 Cronograma saudável. {completed}/{total} marcos concluídos ({progress:.0f}%)."

    def suggest_replan(self, project_id: int) -> Dict:
        """Suggest schedule replan options."""
        from models import Project, Milestone

        project = Project.query.get(project_id)
        if not project:
            return {}

        milestones = Milestone.query.filter_by(project_id=project_id).filter(
            Milestone.status != 'Concluído'
        ).order_by(Milestone.end_date).all()

        suggestions = {
            'compression': {
                'name': 'Compressão de Cronograma',
                'description': 'Adicionar recursos para acelerar entregas críticas',
                'estimated_recovery': '30-50% do atraso',
                'risk': 'Aumento de custo'
            },
            'parallelization': {
                'name': 'Paralelização',
                'description': 'Executar atividades em paralelo onde dependências permitirem',
                'estimated_recovery': '20-40% do atraso',
                'risk': 'Complexidade de coordenação'
            },
            'scope_reduction': {
                'name': 'Redução de Escopo',
                'description': 'Adiar entregas de menor prioridade para fase posterior',
                'estimated_recovery': '40-60% do atraso',
                'risk': 'Impacto em benefícios esperados'
            },
            'fast_tracking': {
                'name': 'Fast Tracking',
                'description': 'Iniciar fases seguintes antes da conclusão das anteriores',
                'estimated_recovery': '25-35% do atraso',
                'risk': 'Retrabalho se houver mudanças'
            }
        }

        return {
            'project': project.title,
            'pending_milestones': len(milestones),
            'suggestions': suggestions
        }
