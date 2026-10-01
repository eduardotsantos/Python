"""
Risk Agent - Monitors and analyzes project risks.
Suggests mitigation plans and identifies emerging risks.
"""
from datetime import datetime, date, timedelta
from typing import Optional, List
from .base import (
    BaseAgent, AgentResult, Insight, ActionSuggestion,
    Severity, HealthStatus, ActionType
)


class RiskAgent(BaseAgent):
    """
    Agente de Riscos.
    Monitors open risks, probability, impact, and mitigation plans.
    """

    @property
    def name(self) -> str:
        return 'risk_agent'

    @property
    def display_name(self) -> str:
        return 'Agente de Riscos'

    @property
    def description(self) -> str:
        return 'Monitora riscos, probabilidades, impactos e planos de mitigação'

    @property
    def icon(self) -> str:
        return 'bi-exclamation-triangle'

    @property
    def color(self) -> str:
        return 'danger'

    def analyze(self, project_id: Optional[int] = None) -> AgentResult:
        self._start_execution()

        from models import Risk, Project

        insights = []
        actions = []
        metrics = {
            'total_risks': 0,
            'critical_risks': 0,
            'high_risks': 0,
            'risks_no_owner': 0,
            'risks_no_plan': 0,
            'overdue_reviews': 0,
            'by_category': {},
            'by_status': {}
        }

        query = Risk.query.filter_by(tenant_id=self.tenant_id)
        if project_id:
            query = query.filter_by(project_id=project_id)

        query = query.filter(Risk.status.notin_(['Fechado', 'Mitigado']))
        risks = query.all()

        metrics['total_risks'] = len(risks)

        for risk in risks:
            score = risk.risk_score
            if score >= 16:
                metrics['critical_risks'] += 1
            elif score >= 9:
                metrics['high_risks'] += 1

            if not risk.owner_id:
                metrics['risks_no_owner'] += 1

            if not risk.mitigation_plan:
                metrics['risks_no_plan'] += 1

            if risk.review_date and risk.review_date < date.today():
                metrics['overdue_reviews'] += 1

            category = risk.category or 'Não categorizado'
            metrics['by_category'][category] = metrics['by_category'].get(category, 0) + 1

            status = risk.status or 'Identificado'
            metrics['by_status'][status] = metrics['by_status'].get(status, 0) + 1

        critical_risks = [r for r in risks if r.risk_score >= 16]
        for risk in critical_risks:
            project = Project.query.get(risk.project_id) if risk.project_id else None
            insights.append(self.create_insight(
                title=f'Risco crítico: {risk.title}',
                description=f'Score {risk.risk_score} (Prob: {risk.probability}, Impacto: {risk.impact}). {risk.description or ""}',
                severity=Severity.CRITICAL,
                category='critical_risk',
                project_id=risk.project_id,
                project_name=project.title if project else None,
                metric_name='risk_score',
                metric_value=risk.risk_score,
                recommendation=risk.mitigation_plan or 'Definir plano de mitigação urgente.',
                data={'risk_id': risk.id, 'category': risk.category}
            ))

            if not risk.mitigation_plan:
                actions.append(self.suggest_action(
                    action_type=ActionType.CREATE_ACTION,
                    title=f'Criar plano de mitigação',
                    description=f'Risco crítico "{risk.title}" precisa de plano de mitigação urgente.',
                    priority=Severity.CRITICAL,
                    project_id=risk.project_id,
                    data={'risk_id': risk.id, 'auto_generate': True}
                ))

        risks_no_owner = [r for r in risks if not r.owner_id and r.risk_score >= 9]
        if risks_no_owner:
            insights.append(self.create_insight(
                title=f'{len(risks_no_owner)} riscos altos sem responsável',
                description='Riscos de alto impacto não possuem responsável definido.',
                severity=Severity.HIGH,
                category='governance',
                recommendation='Atribuir responsáveis para todos os riscos significativos.'
            ))

        risks_no_plan = [r for r in risks if not r.mitigation_plan and r.risk_score >= 6]
        if risks_no_plan:
            insights.append(self.create_insight(
                title=f'{len(risks_no_plan)} riscos sem plano de mitigação',
                description='Riscos médios/altos identificados sem estratégia de tratamento.',
                severity=Severity.MEDIUM,
                category='mitigation'
            ))

        overdue_review_risks = [r for r in risks if r.review_date and r.review_date < date.today()]
        if overdue_review_risks:
            days_overdue = max((date.today() - r.review_date).days for r in overdue_review_risks)
            insights.append(self.create_insight(
                title=f'{len(overdue_review_risks)} riscos com revisão atrasada',
                description=f'Riscos com data de revisão vencida há até {days_overdue} dias.',
                severity=Severity.MEDIUM,
                category='review',
                recommendation='Realizar revisão periódica dos riscos cadastrados.'
            ))

            actions.append(self.suggest_action(
                action_type=ActionType.SCHEDULE_MEETING,
                title='Agendar revisão de riscos',
                description=f'Revisar {len(overdue_review_risks)} riscos com revisão atrasada.',
                priority=Severity.MEDIUM,
                data={'risk_ids': [r.id for r in overdue_review_risks[:10]]}
            ))

        emerging_patterns = self._detect_risk_patterns(risks)
        insights.extend(emerging_patterns)

        overall_status = HealthStatus.HEALTHY
        if metrics['critical_risks'] > 0:
            overall_status = HealthStatus.CRITICAL
        elif metrics['high_risks'] > 0 or metrics['risks_no_plan'] > 3:
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

    def _detect_risk_patterns(self, risks: list) -> List[Insight]:
        """Detect patterns in risks across projects."""
        insights = []

        category_counts = {}
        for risk in risks:
            cat = risk.category or 'Outros'
            category_counts[cat] = category_counts.get(cat, 0) + 1

        for category, count in category_counts.items():
            if count >= 5:
                insights.append(self.create_insight(
                    title=f'Padrão de riscos: {category}',
                    description=f'Identificados {count} riscos na categoria "{category}". Possível causa raiz comum.',
                    severity=Severity.MEDIUM,
                    category='pattern',
                    recommendation=f'Investigar causa raiz dos riscos de {category} para ação preventiva.'
                ))

        recent_risks = [r for r in risks if r.created_at and r.created_at.date() >= date.today() - timedelta(days=7)]
        if len(recent_risks) >= 5:
            insights.append(self.create_insight(
                title=f'{len(recent_risks)} novos riscos esta semana',
                description='Alto volume de novos riscos identificados nos últimos 7 dias.',
                severity=Severity.MEDIUM,
                category='trend',
                recommendation='Revisar processos para identificação proativa de riscos.'
            ))

        return insights

    def _generate_summary(self, metrics: dict, status: HealthStatus) -> str:
        """Generate executive summary."""
        total = metrics['total_risks']
        critical = metrics['critical_risks']
        high = metrics['high_risks']
        no_plan = metrics['risks_no_plan']

        if status == HealthStatus.CRITICAL:
            return f"🔴 {critical} risco(s) crítico(s) de {total} abertos. Ação imediata necessária."
        elif status == HealthStatus.ATTENTION:
            return f"🟡 {total} riscos abertos: {high} alto(s), {no_plan} sem plano de mitigação."
        else:
            return f"🟢 {total} riscos abertos sob controle. Nenhum crítico identificado."

    def suggest_mitigation_plan(self, risk_id: int) -> str:
        """Generate AI-powered mitigation plan suggestion."""
        from models import Risk

        risk = Risk.query.get(risk_id)
        if not risk:
            return "Risco não encontrado."

        category_strategies = {
            'Técnico': [
                'Realizar prova de conceito antes da implementação completa',
                'Contratar consultoria especializada para validação',
                'Criar protótipos incrementais para mitigar incertezas técnicas'
            ],
            'Financeiro': [
                'Provisionar reserva de contingência de 10-15%',
                'Buscar fontes alternativas de financiamento',
                'Renegociar contratos com fornecedores'
            ],
            'Cronograma': [
                'Adicionar buffer de tempo nos marcos críticos',
                'Paralelizar atividades onde possível',
                'Contratar recursos adicionais temporários'
            ],
            'Recursos': [
                'Treinar backup para recursos críticos',
                'Contratar temporários para sobrecarga',
                'Redistribuir carga entre equipes'
            ],
            'Externo': [
                'Diversificar fornecedores',
                'Manter comunicação frequente com stakeholders',
                'Criar planos de contingência para cenários externos'
            ]
        }

        strategies = category_strategies.get(risk.category, [
            'Documentar o risco e comunicar stakeholders',
            'Monitorar indicadores de materialização',
            'Definir gatilhos para ativação do plano de contingência'
        ])

        plan = f"Plano de Mitigação para: {risk.title}\n\n"
        plan += f"Categoria: {risk.category}\n"
        plan += f"Score: {risk.risk_score} (P:{risk.probability} x I:{risk.impact})\n\n"
        plan += "Estratégias sugeridas:\n"
        for i, s in enumerate(strategies, 1):
            plan += f"{i}. {s}\n"

        return plan
