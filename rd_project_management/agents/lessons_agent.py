"""
Lessons Learned Agent - Extracts and catalogs lessons from project history.
Analyzes: Meeting minutes, decisions, documents to generate knowledge base.
"""
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict
import re
from .base import (
    BaseAgent, AgentResult, Insight, ActionSuggestion,
    Severity, HealthStatus, ActionType
)


class LessonsLearnedAgent(BaseAgent):
    """
    Agente de IA para Lições Aprendidas.
    Extracts lessons from project history and builds knowledge base.
    """

    @property
    def name(self) -> str:
        return 'lessons_agent'

    @property
    def display_name(self) -> str:
        return 'Agente de Lições Aprendidas'

    @property
    def description(self) -> str:
        return 'Analisa atas, decisões e documentos para gerar base de conhecimento'

    @property
    def icon(self) -> str:
        return 'bi-lightbulb'

    @property
    def color(self) -> str:
        return 'warning'

    def analyze(self, project_id: Optional[int] = None) -> AgentResult:
        self._start_execution()

        from models import Project, MeetingMinutes, Risk, NonConformity, Bug

        insights = []
        actions = []
        metrics = {
            'total_lessons': 0,
            'from_risks': 0,
            'from_nc': 0,
            'from_bugs': 0,
            'from_meetings': 0,
            'patterns_identified': 0
        }

        query = Project.query.filter_by(tenant_id=self.tenant_id)
        if project_id:
            query = query.filter_by(id=project_id)

        projects = query.all()

        for project in projects:
            project_lessons = self._extract_project_lessons(project)
            insights.extend(project_lessons['insights'])
            metrics['from_risks'] += project_lessons['from_risks']
            metrics['from_nc'] += project_lessons['from_nc']
            metrics['from_bugs'] += project_lessons['from_bugs']
            metrics['from_meetings'] += project_lessons['from_meetings']

        patterns = self._identify_patterns(projects)
        insights.extend(patterns['insights'])
        metrics['patterns_identified'] = patterns['count']

        metrics['total_lessons'] = (
            metrics['from_risks'] + metrics['from_nc'] +
            metrics['from_bugs'] + metrics['from_meetings']
        )

        recommendations = self._generate_recommendations(insights)
        actions.extend(recommendations)

        overall_status = HealthStatus.HEALTHY
        if metrics['patterns_identified'] > 3:
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

    def _extract_project_lessons(self, project) -> Dict:
        """Extract lessons learned from a single project."""
        from models import Risk, NonConformity, Bug, MeetingMinutes

        insights = []
        from_risks = 0
        from_nc = 0
        from_bugs = 0
        from_meetings = 0

        mitigated_risks = Risk.query.filter_by(
            project_id=project.id,
            status='Mitigado'
        ).all()

        for risk in mitigated_risks:
            if risk.mitigation_plan:
                from_risks += 1
                insights.append(self.create_insight(
                    title=f'Lição: Mitigação de risco bem-sucedida',
                    description=f'Risco "{risk.title}" mitigado com: {risk.mitigation_plan[:200]}',
                    severity=Severity.INFO,
                    category='lesson_risk',
                    project_id=project.id,
                    project_name=project.title,
                    recommendation=f'Considerar estratégia similar para riscos de categoria {risk.category}.'
                ))

        closed_ncs = NonConformity.query.filter_by(
            project_id=project.id,
            status='Fechada'
        ).all()

        for nc in closed_ncs:
            if nc.root_cause and nc.corrective_plan:
                from_nc += 1
                insights.append(self.create_insight(
                    title=f'Lição: NC tratada com sucesso',
                    description=f'Causa raiz: {nc.root_cause[:100]}. Ação: {nc.corrective_plan[:100]}',
                    severity=Severity.INFO,
                    category='lesson_nc',
                    project_id=project.id,
                    project_name=project.title
                ))

        resolved_bugs = Bug.query.filter_by(
            project_id=project.id
        ).filter(Bug.status.in_(['Resolvido', 'Fechado'])).all()

        for bug in resolved_bugs:
            if bug.resolution_notes and bug.severity in ['Crítica', 'Alta']:
                from_bugs += 1
                insights.append(self.create_insight(
                    title=f'Lição: Correção de bug {bug.severity.lower()}',
                    description=f'Bug "{bug.title}": {bug.resolution_notes[:150] if bug.resolution_notes else "Resolvido"}',
                    severity=Severity.INFO,
                    category='lesson_bug',
                    project_id=project.id,
                    project_name=project.title
                ))

        try:
            minutes = MeetingMinutes.query.filter_by(project_id=project.id).all()
            for minute in minutes:
                lessons_from_minute = self._extract_lessons_from_minutes(minute)
                from_meetings += len(lessons_from_minute)
                insights.extend(lessons_from_minute)
        except:
            pass

        return {
            'insights': insights,
            'from_risks': from_risks,
            'from_nc': from_nc,
            'from_bugs': from_bugs,
            'from_meetings': from_meetings
        }

    def _extract_lessons_from_minutes(self, minutes) -> List[Insight]:
        """Extract lessons from meeting minutes content."""
        lessons = []

        if not hasattr(minutes, 'content') or not minutes.content:
            return lessons

        content = minutes.content.lower()

        lesson_patterns = [
            (r'lição aprendida[:\s]+(.+?)(?:\.|$)', 'Lição documentada em ata'),
            (r'para futuros projetos[:\s]+(.+?)(?:\.|$)', 'Recomendação para projetos futuros'),
            (r'evitar no futuro[:\s]+(.+?)(?:\.|$)', 'Prática a evitar'),
            (r'boa prática[:\s]+(.+?)(?:\.|$)', 'Boa prática identificada'),
        ]

        for pattern, category in lesson_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                if len(match) > 20:
                    lessons.append(self.create_insight(
                        title=category,
                        description=match[:200].capitalize(),
                        severity=Severity.INFO,
                        category='lesson_meeting'
                    ))

        return lessons

    def _identify_patterns(self, projects: list) -> Dict:
        """Identify recurring patterns across projects."""
        from models import Risk, NonConformity, Bug

        insights = []
        pattern_count = 0

        risk_categories = {}
        nc_types = {}
        bug_severities = {}

        for project in projects:
            risks = Risk.query.filter_by(project_id=project.id).all()
            for risk in risks:
                cat = risk.category or 'Outros'
                risk_categories[cat] = risk_categories.get(cat, 0) + 1

            ncs = NonConformity.query.filter_by(project_id=project.id).all()
            for nc in ncs:
                t = nc.nc_type or 'Outros'
                nc_types[t] = nc_types.get(t, 0) + 1

            bugs = Bug.query.filter_by(project_id=project.id).all()
            for bug in bugs:
                sev = bug.severity or 'Média'
                bug_severities[sev] = bug_severities.get(sev, 0) + 1

        for category, count in risk_categories.items():
            if count >= 5:
                pattern_count += 1
                insights.append(self.create_insight(
                    title=f'Padrão: Riscos de {category}',
                    description=f'{count} riscos da categoria "{category}" identificados em múltiplos projetos.',
                    severity=Severity.MEDIUM,
                    category='pattern_risk',
                    recommendation=f'Implementar controles preventivos para riscos de {category}.'
                ))

        for nc_type, count in nc_types.items():
            if count >= 5:
                pattern_count += 1
                insights.append(self.create_insight(
                    title=f'Padrão: NCs de {nc_type}',
                    description=f'{count} não conformidades do tipo "{nc_type}" são recorrentes.',
                    severity=Severity.MEDIUM,
                    category='pattern_nc',
                    recommendation=f'Revisar processos relacionados a {nc_type}.'
                ))

        critical_bugs = bug_severities.get('Crítica', 0)
        if critical_bugs >= 5:
            pattern_count += 1
            insights.append(self.create_insight(
                title='Padrão: Alto volume de bugs críticos',
                description=f'{critical_bugs} bugs críticos registrados no portfolio.',
                severity=Severity.HIGH,
                category='pattern_bug',
                recommendation='Intensificar testes antes de releases e revisar processo de QA.'
            ))

        return {'insights': insights, 'count': pattern_count}

    def _generate_recommendations(self, insights: List[Insight]) -> List[ActionSuggestion]:
        """Generate actionable recommendations from lessons."""
        actions = []

        pattern_insights = [i for i in insights if i.category.startswith('pattern_')]

        if len(pattern_insights) > 0:
            actions.append(self.suggest_action(
                action_type=ActionType.GENERATE_REPORT,
                title='Gerar relatório de lições aprendidas',
                description=f'{len(pattern_insights)} padrões identificados requerem documentação.',
                priority=Severity.MEDIUM,
                data={'pattern_count': len(pattern_insights)}
            ))

        lesson_insights = [i for i in insights if i.category.startswith('lesson_')]
        if len(lesson_insights) >= 10:
            actions.append(self.suggest_action(
                action_type=ActionType.CREATE_ACTION,
                title='Atualizar base de conhecimento',
                description=f'{len(lesson_insights)} lições identificadas para catalogação.',
                priority=Severity.LOW,
                data={'lesson_count': len(lesson_insights)}
            ))

        return actions

    def _generate_summary(self, metrics: Dict, status: HealthStatus) -> str:
        """Generate executive summary."""
        total = metrics['total_lessons']
        patterns = metrics['patterns_identified']

        if patterns > 3:
            return f"🟡 {total} lições identificadas. {patterns} padrões recorrentes detectados."
        elif total > 0:
            return f"🟢 {total} lições catalogadas. Base de conhecimento atualizada."
        else:
            return f"ℹ️ Nenhuma nova lição identificada nesta análise."

    def generate_knowledge_base_entry(self, insight: Insight) -> Dict:
        """Generate a structured knowledge base entry from an insight."""
        return {
            'title': insight.title,
            'description': insight.description,
            'category': insight.category,
            'project': insight.project_name,
            'recommendation': insight.recommendation,
            'date': date.today().isoformat(),
            'source': 'ai_extraction'
        }
