"""
Project Advisor Agent - The AI-powered strategic advisor.
Provides recommendations based on historical analysis and best practices.
"""
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict
from .base import (
    BaseAgent, AgentResult, Insight, ActionSuggestion,
    Severity, HealthStatus, ActionType
)


class ProjectAdvisorAgent(BaseAgent):
    """
    Agente Conselheiro de Projetos.
    Provides AI-powered recommendations and strategic guidance.
    This is the differentiator - it doesn't just inform, it recommends.
    """

    @property
    def name(self) -> str:
        return 'advisor_agent'

    @property
    def display_name(self) -> str:
        return 'Conselheiro de Projetos IA'

    @property
    def description(self) -> str:
        return 'Fornece recomendações estratégicas baseadas em análise histórica'

    @property
    def icon(self) -> str:
        return 'bi-robot'

    @property
    def color(self) -> str:
        return 'primary'

    def analyze(self, project_id: Optional[int] = None) -> AgentResult:
        self._start_execution()

        from models import Project

        insights = []
        actions = []
        metrics = {
            'total_projects_analyzed': 0,
            'recommendations_generated': 0,
            'high_priority_recommendations': 0,
            'patterns_detected': 0,
            'success_probability': {}
        }

        query = Project.query.filter_by(tenant_id=self.tenant_id)
        if project_id:
            query = query.filter_by(id=project_id)
        else:
            query = query.filter(Project.status.in_(['Em Andamento', 'Planejamento']))

        projects = query.all()
        metrics['total_projects_analyzed'] = len(projects)

        for project in projects:
            project_advice = self._analyze_and_advise(project)
            insights.extend(project_advice['insights'])
            actions.extend(project_advice['actions'])
            metrics['recommendations_generated'] += project_advice['recommendation_count']

            if project_advice['success_probability']:
                metrics['success_probability'][project.id] = project_advice['success_probability']

        portfolio_advice = self._portfolio_level_advice(projects)
        insights.extend(portfolio_advice['insights'])
        actions.extend(portfolio_advice['actions'])

        metrics['high_priority_recommendations'] = sum(
            1 for a in actions if a.priority in [Severity.HIGH, Severity.CRITICAL]
        )

        overall_status = HealthStatus.HEALTHY
        if metrics['high_priority_recommendations'] > 3:
            overall_status = HealthStatus.ATTENTION
        if any(p < 50 for p in metrics['success_probability'].values()):
            overall_status = HealthStatus.CRITICAL

        summary = self._generate_summary(metrics, overall_status)

        return self.create_result(
            success=True,
            insights=insights,
            actions=actions,
            summary=summary,
            health_status=overall_status,
            metrics=metrics
        )

    def _analyze_and_advise(self, project) -> Dict:
        """Provide AI-powered advice for a single project."""
        from models import Milestone, Expense, Risk, PendingItem

        insights = []
        actions = []
        recommendation_count = 0

        success_prob = self._calculate_success_probability(project)

        milestones = Milestone.query.filter_by(project_id=project.id).all()
        completed = sum(1 for m in milestones if m.status == 'Concluído')
        total_m = len(milestones)
        progress = (completed / total_m * 100) if total_m > 0 else 0

        expenses = Expense.query.filter_by(project_id=project.id).all()
        spent = sum(e.amount for e in expenses)
        budget = project.budget or 0
        consumption = (spent / budget * 100) if budget > 0 else 0

        if success_prob < 50:
            recommendation_count += 1
            insights.append(self.create_insight(
                title=f'Projeto em risco: {success_prob:.0f}% probabilidade de sucesso',
                description=f'Análise indica alto risco de não atingir objetivos para {project.title}.',
                severity=Severity.CRITICAL,
                category='success_prediction',
                project_id=project.id,
                project_name=project.title,
                metric_name='success_probability',
                metric_value=success_prob,
                recommendation='Considerar revisão de escopo, prazo ou recursos.'
            ))

        if consumption > progress + 15 and progress > 20:
            recommendation_count += 1
            variance = consumption - progress

            advice = self._generate_budget_advice(project, consumption, progress, variance)
            insights.append(self.create_insight(
                title=f'Recomendação: Ajuste orçamentário necessário',
                description=f'Desvio de {variance:.0f}pp entre consumo ({consumption:.0f}%) e progresso ({progress:.0f}%).',
                severity=Severity.HIGH,
                category='budget_advice',
                project_id=project.id,
                project_name=project.title,
                recommendation=advice
            ))

            actions.append(self.suggest_action(
                action_type=ActionType.CREATE_SCENARIO,
                title='Gerar cenários de ajuste',
                description=f'Criar cenários alternativos para {project.title}',
                priority=Severity.HIGH,
                project_id=project.id,
                data={'variance': variance, 'consumption': consumption, 'progress': progress}
            ))

        overdue = [m for m in milestones if m.status != 'Concluído' and m.end_date and m.end_date < date.today()]
        if len(overdue) > 0:
            recommendation_count += 1
            days_late = max((date.today() - m.end_date).days for m in overdue)

            advice = self._generate_schedule_advice(project, overdue, days_late, progress)
            insights.append(self.create_insight(
                title=f'Recomendação: Recuperação de cronograma',
                description=f'{len(overdue)} marco(s) atrasado(s), máximo {days_late} dias.',
                severity=Severity.HIGH if days_late > 14 else Severity.MEDIUM,
                category='schedule_advice',
                project_id=project.id,
                project_name=project.title,
                recommendation=advice
            ))

            if days_late > 7:
                actions.append(self.suggest_action(
                    action_type=ActionType.SCHEDULE_MEETING,
                    title='Reunião de recovery',
                    description=f'Alinhar plano de recuperação para {project.title}',
                    priority=Severity.HIGH,
                    project_id=project.id,
                    data={'days_late': days_late, 'overdue_count': len(overdue)},
                    auto_executable=True
                ))

        risks = Risk.query.filter_by(project_id=project.id).filter(
            Risk.status.notin_(['Fechado', 'Mitigado'])
        ).all()
        high_risks = [r for r in risks if r.risk_score >= 12]

        if high_risks:
            recommendation_count += 1
            advice = self._generate_risk_advice(project, high_risks)
            insights.append(self.create_insight(
                title=f'Recomendação: Gestão proativa de riscos',
                description=f'{len(high_risks)} risco(s) de alto impacto identificado(s).',
                severity=Severity.HIGH,
                category='risk_advice',
                project_id=project.id,
                project_name=project.title,
                recommendation=advice
            ))

        return {
            'insights': insights,
            'actions': actions,
            'recommendation_count': recommendation_count,
            'success_probability': success_prob
        }

    def _calculate_success_probability(self, project) -> float:
        """Calculate project success probability based on multiple factors."""
        from models import Milestone, Expense, Risk

        probability = 100

        milestones = Milestone.query.filter_by(project_id=project.id).all()
        if milestones:
            completed = sum(1 for m in milestones if m.status == 'Concluído')
            progress = completed / len(milestones)

            overdue = [m for m in milestones if m.status != 'Concluído' and m.end_date and m.end_date < date.today()]
            overdue_ratio = len(overdue) / len(milestones) if milestones else 0
            probability -= overdue_ratio * 30

        expenses = Expense.query.filter_by(project_id=project.id).all()
        spent = sum(e.amount for e in expenses)
        budget = project.budget or 0

        if budget > 0:
            consumption = spent / budget
            expected_consumption = progress if milestones else 0.5

            if consumption > expected_consumption + 0.2:
                probability -= (consumption - expected_consumption) * 50

        risks = Risk.query.filter_by(project_id=project.id).filter(
            Risk.status.notin_(['Fechado', 'Mitigado'])
        ).all()

        high_risks = sum(1 for r in risks if r.risk_score >= 12)
        probability -= high_risks * 10

        if project.end_date and project.end_date < date.today() and project.status != 'Concluído':
            days_over = (date.today() - project.end_date).days
            probability -= min(30, days_over)

        return max(0, min(100, probability))

    def _generate_budget_advice(self, project, consumption: float, progress: float, variance: float) -> str:
        """Generate specific budget advice."""
        if variance > 30:
            return (
                f"Desvio crítico de {variance:.0f}pp. Recomendo: "
                f"1) Solicitar aporte adicional de ~{(project.budget * variance/100):,.0f} "
                f"ou 2) Reduzir escopo em ~{variance:.0f}% das entregas restantes."
            )
        elif variance > 15:
            return (
                f"Desvio significativo. Sugestões: "
                f"1) Renegociar contratos de fornecedores, "
                f"2) Postergar entregas não críticas, "
                f"3) Aumentar eficiência da equipe."
            )
        else:
            return (
                f"Desvio moderado de {variance:.0f}pp. Monitorar nas próximas 2 semanas. "
                f"Se persistir, considerar ajustes no planejamento."
            )

    def _generate_schedule_advice(self, project, overdue: list, max_delay: int, progress: float) -> str:
        """Generate specific schedule advice."""
        remaining_progress = 100 - progress

        if max_delay > 30:
            return (
                f"Atraso crítico de {max_delay} dias. Recomendo: "
                f"1) Reunião de war room para recovery, "
                f"2) Avaliar compressão com recursos extras, "
                f"3) Considerar redefinição de baseline."
            )
        elif max_delay > 14:
            return (
                f"Atraso significativo. Sugestões: "
                f"1) Fast-tracking de atividades paralelas, "
                f"2) Adicionar recursos para marcos críticos, "
                f"3) Revisar dependências para otimização."
            )
        else:
            return (
                f"Atraso recuperável de {max_delay} dias. "
                f"Intensificar acompanhamento e considerar horas extras controladas."
            )

    def _generate_risk_advice(self, project, high_risks: list) -> str:
        """Generate specific risk management advice."""
        categories = [r.category for r in high_risks if r.category]
        unique_categories = list(set(categories))

        if len(high_risks) > 3:
            return (
                f"{len(high_risks)} riscos de alto impacto requerem plano de contingência. "
                f"Categorias predominantes: {', '.join(unique_categories[:3])}. "
                f"Recomendo revisão geral da estratégia de riscos com stakeholders."
            )
        else:
            risk_details = ", ".join([r.title[:30] for r in high_risks[:3]])
            return (
                f"Riscos prioritários: {risk_details}. "
                f"Definir planos de mitigação específicos e datas de revisão."
            )

    def _portfolio_level_advice(self, projects: list) -> Dict:
        """Provide portfolio-level strategic advice."""
        insights = []
        actions = []

        if not projects:
            return {'insights': insights, 'actions': actions}

        total_budget = sum(p.budget or 0 for p in projects)
        from models import Expense
        total_spent = sum(
            sum(e.amount for e in Expense.query.filter_by(project_id=p.id).all())
            for p in projects
        )

        portfolio_consumption = (total_spent / total_budget * 100) if total_budget > 0 else 0

        active_projects = len([p for p in projects if p.status == 'Em Andamento'])
        if active_projects > 10:
            insights.append(self.create_insight(
                title='Recomendação: Avaliar capacidade do portfolio',
                description=f'{active_projects} projetos simultâneos. Risco de dispersão de recursos.',
                severity=Severity.MEDIUM,
                category='portfolio_advice',
                recommendation='Considerar priorização e possível postergação de projetos de menor impacto.'
            ))

        probabilities = [self._calculate_success_probability(p) for p in projects]
        avg_probability = sum(probabilities) / len(probabilities) if probabilities else 100

        if avg_probability < 70:
            insights.append(self.create_insight(
                title='Alerta: Portfolio com risco elevado',
                description=f'Probabilidade média de sucesso: {avg_probability:.0f}%.',
                severity=Severity.HIGH,
                category='portfolio_risk',
                recommendation='Intensificar governança e considerar revisão estratégica do portfolio.'
            ))

        return {'insights': insights, 'actions': actions}

    def _generate_summary(self, metrics: Dict, status: HealthStatus) -> str:
        """Generate executive summary."""
        recs = metrics['recommendations_generated']
        high = metrics['high_priority_recommendations']
        analyzed = metrics['total_projects_analyzed']

        if status == HealthStatus.CRITICAL:
            return f"🔴 {high} recomendação(ões) crítica(s) de {recs} total. Ação imediata necessária."
        elif status == HealthStatus.ATTENTION:
            return f"🟡 {recs} recomendações geradas para {analyzed} projetos. {high} de alta prioridade."
        else:
            return f"🟢 {analyzed} projetos analisados. {recs} recomendações de melhoria."

    def get_project_recommendation(self, project_id: int) -> Dict:
        """Get detailed recommendation for a specific project."""
        from models import Project

        project = Project.query.get(project_id)
        if not project:
            return {'error': 'Projeto não encontrado'}

        advice = self._analyze_and_advise(project)
        success_prob = advice['success_probability']

        return {
            'project': project.title,
            'success_probability': success_prob,
            'risk_level': 'Alto' if success_prob < 50 else 'Médio' if success_prob < 75 else 'Baixo',
            'insights': [i.to_dict() for i in advice['insights']],
            'recommended_actions': [a.to_dict() for a in advice['actions']],
            'generated_at': datetime.utcnow().isoformat()
        }
