"""
Financial Agent (Board Finance AI) - Analyzes project finances.
Monitors: Budget, Realized, Forecast, Burn Rate, ROI.
"""
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict
from .base import (
    BaseAgent, AgentResult, Insight, ActionSuggestion,
    Severity, HealthStatus, ActionType
)


class FinancialAgent(BaseAgent):
    """
    Agente Financeiro (Board Finance AI).
    Analyzes budget, expenditure, and financial projections.
    """

    @property
    def name(self) -> str:
        return 'financial_agent'

    @property
    def display_name(self) -> str:
        return 'Agente Financeiro'

    @property
    def description(self) -> str:
        return 'Analisa orçamento, realizado, forecast, burn rate e ROI'

    @property
    def icon(self) -> str:
        return 'bi-cash-stack'

    @property
    def color(self) -> str:
        return 'success'

    def analyze(self, project_id: Optional[int] = None) -> AgentResult:
        self._start_execution()

        from models import Project, Expense, Milestone

        insights = []
        actions = []
        metrics = {
            'total_budget': 0,
            'total_spent': 0,
            'total_committed': 0,
            'avg_burn_rate': 0,
            'projects_over_budget': 0,
            'projects_at_risk': 0,
            'projects_healthy': 0,
            'project_details': []
        }

        query = Project.query.filter_by(tenant_id=self.tenant_id)
        if project_id:
            query = query.filter_by(id=project_id)
        else:
            query = query.filter(Project.status.in_(['Em Andamento', 'Planejamento']))

        projects = query.all()

        for project in projects:
            analysis = self._analyze_project_finance(project)
            metrics['project_details'].append(analysis)

            metrics['total_budget'] += analysis['budget']
            metrics['total_spent'] += analysis['spent']

            if analysis['status'] == 'over_budget':
                metrics['projects_over_budget'] += 1
            elif analysis['status'] == 'at_risk':
                metrics['projects_at_risk'] += 1
            else:
                metrics['projects_healthy'] += 1

            insights.extend(analysis['insights'])
            actions.extend(analysis['actions'])

        if metrics['total_budget'] > 0:
            metrics['consumption_pct'] = (metrics['total_spent'] / metrics['total_budget']) * 100
        else:
            metrics['consumption_pct'] = 0

        portfolio_insights = self._analyze_portfolio_finance(metrics)
        insights.extend(portfolio_insights)

        overall_status = HealthStatus.HEALTHY
        if metrics['projects_over_budget'] > 0:
            overall_status = HealthStatus.CRITICAL
        elif metrics['projects_at_risk'] > 0:
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

    def _analyze_project_finance(self, project) -> Dict:
        """Analyze financial health of a single project."""
        from models import Expense, Milestone

        insights = []
        actions = []

        expenses = Expense.query.filter_by(project_id=project.id).all()
        total_spent = sum(e.amount for e in expenses)
        budget = project.budget or 0

        milestones = Milestone.query.filter_by(project_id=project.id).all()
        completed = sum(1 for m in milestones if m.status == 'Concluído')
        total_milestones = len(milestones)
        progress_pct = (completed / total_milestones * 100) if total_milestones > 0 else 0

        consumption_pct = (total_spent / budget * 100) if budget > 0 else 0

        burn_rate = self._calculate_burn_rate(project, expenses)
        forecast = self._calculate_forecast(project, total_spent, burn_rate, progress_pct)

        status = 'healthy'
        if budget > 0:
            if consumption_pct > 100:
                status = 'over_budget'
                insights.append(self.create_insight(
                    title=f'Projeto acima do orçamento',
                    description=f'Consumido {consumption_pct:.1f}% do orçamento (R$ {total_spent:,.2f} de R$ {budget:,.2f}).',
                    severity=Severity.CRITICAL,
                    category='over_budget',
                    project_id=project.id,
                    project_name=project.title,
                    metric_name='consumo_percentual',
                    metric_value=consumption_pct,
                    metric_threshold=100,
                    recommendation='Avaliar redução de escopo ou solicitação de verba adicional.'
                ))

                actions.append(self.suggest_action(
                    action_type=ActionType.CREATE_SCENARIO,
                    title='Gerar cenários de recuperação',
                    description=f'Criar cenários para projeto {project.title} acima do orçamento.',
                    priority=Severity.CRITICAL,
                    project_id=project.id,
                    data={'consumption': consumption_pct, 'spent': total_spent, 'budget': budget}
                ))

            elif consumption_pct > progress_pct + 20:
                status = 'at_risk'
                insights.append(self.create_insight(
                    title=f'Desvio orçamentário significativo',
                    description=f'Consumiu {consumption_pct:.0f}% do orçamento com {progress_pct:.0f}% de progresso.',
                    severity=Severity.HIGH,
                    category='budget_variance',
                    project_id=project.id,
                    project_name=project.title,
                    metric_name='desvio',
                    metric_value=consumption_pct - progress_pct,
                    recommendation='Revisar previsão de gastos e ajustar planejamento.'
                ))

            elif consumption_pct > 80 and progress_pct < 70:
                status = 'at_risk'
                insights.append(self.create_insight(
                    title=f'Alerta de consumo acelerado',
                    description=f'{consumption_pct:.0f}% do orçamento consumido. Apenas {progress_pct:.0f}% concluído.',
                    severity=Severity.MEDIUM,
                    category='burn_rate',
                    project_id=project.id,
                    project_name=project.title
                ))

        if forecast['estimated_total'] > budget * 1.1 and budget > 0:
            insights.append(self.create_insight(
                title=f'Forecast indica estouro',
                description=f'Projeção: R$ {forecast["estimated_total"]:,.2f} (orçamento: R$ {budget:,.2f}).',
                severity=Severity.HIGH,
                category='forecast',
                project_id=project.id,
                project_name=project.title,
                metric_name='forecast_total',
                metric_value=forecast['estimated_total']
            ))

        return {
            'project_id': project.id,
            'project_name': project.title,
            'budget': budget,
            'spent': total_spent,
            'consumption_pct': consumption_pct,
            'progress_pct': progress_pct,
            'burn_rate': burn_rate,
            'forecast': forecast,
            'status': status,
            'insights': insights,
            'actions': actions
        }

    def _calculate_burn_rate(self, project, expenses: list) -> Dict:
        """Calculate monthly burn rate."""
        if not expenses:
            return {'monthly': 0, 'weekly': 0, 'daily': 0}

        if not project.start_date:
            return {'monthly': 0, 'weekly': 0, 'daily': 0}

        total_spent = sum(e.amount for e in expenses)
        days_elapsed = (date.today() - project.start_date).days
        if days_elapsed <= 0:
            days_elapsed = 1

        daily_rate = total_spent / days_elapsed
        weekly_rate = daily_rate * 7
        monthly_rate = daily_rate * 30

        return {
            'monthly': monthly_rate,
            'weekly': weekly_rate,
            'daily': daily_rate,
            'days_elapsed': days_elapsed
        }

    def _calculate_forecast(self, project, spent: float, burn_rate: Dict, progress_pct: float) -> Dict:
        """Calculate financial forecast."""
        if progress_pct > 0:
            estimated_total = (spent / progress_pct) * 100
        elif burn_rate['daily'] > 0 and project.end_date:
            days_remaining = (project.end_date - date.today()).days
            estimated_total = spent + (burn_rate['daily'] * max(0, days_remaining))
        else:
            estimated_total = spent

        budget = project.budget or 0
        variance = estimated_total - budget if budget > 0 else 0
        variance_pct = (variance / budget * 100) if budget > 0 else 0

        return {
            'estimated_total': estimated_total,
            'variance': variance,
            'variance_pct': variance_pct,
            'confidence': 'high' if progress_pct > 50 else 'medium' if progress_pct > 20 else 'low'
        }

    def _analyze_portfolio_finance(self, metrics: Dict) -> List[Insight]:
        """Analyze portfolio-level financial health."""
        insights = []

        if metrics['total_budget'] > 0:
            portfolio_consumption = (metrics['total_spent'] / metrics['total_budget']) * 100

            if portfolio_consumption > 85:
                insights.append(self.create_insight(
                    title='Portfolio com alto consumo',
                    description=f'{portfolio_consumption:.1f}% do orçamento total consumido (R$ {metrics["total_spent"]:,.2f}).',
                    severity=Severity.HIGH if portfolio_consumption > 95 else Severity.MEDIUM,
                    category='portfolio'
                ))

        if metrics['projects_over_budget'] > 0:
            total_projects = len(metrics['project_details'])
            pct_over = (metrics['projects_over_budget'] / total_projects * 100) if total_projects > 0 else 0
            insights.append(self.create_insight(
                title=f'{metrics["projects_over_budget"]} projetos acima do orçamento',
                description=f'{pct_over:.0f}% dos projetos ativos estão acima do orçamento previsto.',
                severity=Severity.CRITICAL,
                category='portfolio'
            ))

        return insights

    def _generate_summary(self, metrics: Dict, status: HealthStatus) -> str:
        """Generate executive summary."""
        total_budget = metrics['total_budget']
        total_spent = metrics['total_spent']
        consumption = metrics.get('consumption_pct', 0)

        if status == HealthStatus.CRITICAL:
            return f"🔴 {metrics['projects_over_budget']} projeto(s) acima do orçamento. Total: R$ {total_spent:,.2f} / R$ {total_budget:,.2f} ({consumption:.0f}%)."
        elif status == HealthStatus.ATTENTION:
            return f"🟡 {metrics['projects_at_risk']} projeto(s) com risco financeiro. Consumo: {consumption:.0f}% do portfolio."
        else:
            return f"🟢 Finanças saudáveis. Consumo: R$ {total_spent:,.2f} de R$ {total_budget:,.2f} ({consumption:.0f}%)."

    def generate_financial_scenarios(self, project_id: int) -> List[Dict]:
        """Generate alternative financial scenarios."""
        from models import Project, Expense, Milestone

        project = Project.query.get(project_id)
        if not project:
            return []

        expenses = Expense.query.filter_by(project_id=project_id).all()
        total_spent = sum(e.amount for e in expenses)
        budget = project.budget or 0
        remaining = budget - total_spent

        milestones = Milestone.query.filter_by(project_id=project_id).all()
        pending = [m for m in milestones if m.status != 'Concluído']

        scenarios = []

        scenarios.append({
            'name': 'Cenário 1: Redução de Escopo',
            'description': 'Remover ou simplificar entregas de menor prioridade',
            'actions': [
                f'Revisar {len(pending)} marcos pendentes',
                'Identificar entregas que podem ser adiadas para fase 2',
                'Renegociar critérios de aceitação'
            ],
            'estimated_savings': remaining * 0.2,
            'risk': 'Médio',
            'timeline_impact': 'Nenhum'
        })

        scenarios.append({
            'name': 'Cenário 2: Aporte Adicional',
            'description': 'Solicitar verba adicional para conclusão',
            'actions': [
                'Preparar justificativa técnica',
                'Calcular valor necessário com margem de 15%',
                'Apresentar para aprovação'
            ],
            'estimated_additional': (total_spent / 0.7) - budget if budget > 0 else total_spent * 0.3,
            'risk': 'Baixo',
            'timeline_impact': 'Possível atraso na aprovação'
        })

        scenarios.append({
            'name': 'Cenário 3: Compressão de Cronograma',
            'description': 'Acelerar entregas para reduzir custos fixos',
            'actions': [
                'Paralelizar atividades onde possível',
                'Adicionar recursos temporários',
                'Intensificar dedicação da equipe'
            ],
            'estimated_savings': remaining * 0.1,
            'risk': 'Alto',
            'timeline_impact': 'Redução de 20% no prazo'
        })

        return scenarios
