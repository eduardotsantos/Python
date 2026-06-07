"""
Compliance Agent - Monitors governance and regulatory compliance.
Analyzes: LGPD, audits, policies, P&D accountability (FINEP, EMBRAPII, FAPESP, etc).
"""
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict
from .base import (
    BaseAgent, AgentResult, Insight, ActionSuggestion,
    Severity, HealthStatus, ActionType
)


class ComplianceAgent(BaseAgent):
    """
    Agente de Compliance e Governança.
    Monitors regulatory compliance, audits, and P&D accountability.
    """

    @property
    def name(self) -> str:
        return 'compliance_agent'

    @property
    def display_name(self) -> str:
        return 'Agente de Compliance e Governança'

    @property
    def description(self) -> str:
        return 'Monitora LGPD, compliance, auditoria e prestação de contas de P&D'

    @property
    def icon(self) -> str:
        return 'bi-shield-lock'

    @property
    def color(self) -> str:
        return 'secondary'

    def analyze(self, project_id: Optional[int] = None) -> AgentResult:
        self._start_execution()

        from models import Project, NonConformity, CorrectiveAction, PendingItem, Expense, Milestone

        insights = []
        actions = []
        metrics = {
            'total_nc': 0,
            'open_nc': 0,
            'audit_findings': 0,
            'documentation_gaps': 0,
            'evidence_missing': 0,
            'pending_accountability': 0,
            'compliance_score': 100,
            'by_project': []
        }

        query = Project.query.filter_by(tenant_id=self.tenant_id)
        if project_id:
            query = query.filter_by(id=project_id)
        else:
            query = query.filter(Project.status.in_(['Em Andamento', 'Planejamento']))

        projects = query.all()

        for project in projects:
            project_compliance = self._analyze_project_compliance(project)
            metrics['by_project'].append(project_compliance)

            metrics['total_nc'] += project_compliance['nc_count']
            metrics['open_nc'] += project_compliance['open_nc']
            metrics['documentation_gaps'] += project_compliance['doc_gaps']
            metrics['evidence_missing'] += project_compliance['evidence_missing']

            insights.extend(project_compliance['insights'])
            actions.extend(project_compliance['actions'])

        metrics['compliance_score'] = self._calculate_compliance_score(metrics)

        portfolio_insights = self._analyze_portfolio_compliance(metrics)
        insights.extend(portfolio_insights)

        overall_status = HealthStatus.HEALTHY
        if metrics['compliance_score'] < 60:
            overall_status = HealthStatus.CRITICAL
        elif metrics['compliance_score'] < 80 or metrics['evidence_missing'] > 0:
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

    def _analyze_project_compliance(self, project) -> Dict:
        """Analyze compliance metrics for a single project."""
        from models import NonConformity, Expense, Milestone, PendingItem

        insights = []
        actions = []
        today = date.today()

        ncs = NonConformity.query.filter_by(project_id=project.id).all()
        open_ncs = [nc for nc in ncs if nc.status != 'Fechada']
        audit_ncs = [nc for nc in ncs if nc.nc_type == 'Auditoria']

        is_funded = self._is_funded_project(project)

        evidence_missing = 0
        doc_gaps = 0

        if is_funded:
            milestones = Milestone.query.filter_by(project_id=project.id, status='Concluído').all()
            for m in milestones:
                if not self._has_evidence(m):
                    evidence_missing += 1

            expenses = Expense.query.filter_by(project_id=project.id).all()
            for e in expenses:
                if not self._has_documentation(e):
                    doc_gaps += 1

            if evidence_missing > 0:
                insights.append(self.create_insight(
                    title=f'{evidence_missing} marco(s) sem evidência',
                    description=f'Entregas concluídas sem evidência documentada em {project.title}.',
                    severity=Severity.HIGH,
                    category='evidence',
                    project_id=project.id,
                    project_name=project.title,
                    metric_name='evidence_missing',
                    metric_value=evidence_missing,
                    recommendation='Documentar evidências antes da próxima prestação de contas.'
                ))

                actions.append(self.suggest_action(
                    action_type=ActionType.CREATE_PENDING,
                    title='Coletar evidências pendentes',
                    description=f'Documentar {evidence_missing} entrega(s) sem evidência.',
                    priority=Severity.HIGH,
                    project_id=project.id,
                    data={'type': 'evidence_collection'}
                ))

            if doc_gaps > 0:
                insights.append(self.create_insight(
                    title=f'{doc_gaps} despesa(s) sem documentação',
                    description=f'Despesas registradas sem documentação fiscal/comprobatória.',
                    severity=Severity.HIGH,
                    category='documentation',
                    project_id=project.id,
                    project_name=project.title,
                    metric_name='doc_gaps',
                    metric_value=doc_gaps,
                    recommendation='Anexar documentação antes da prestação de contas.'
                ))

            accountability_check = self._check_accountability_deadlines(project)
            if accountability_check['due_soon']:
                insights.append(self.create_insight(
                    title='Prestação de contas próxima',
                    description=f'Prazo de prestação de contas em {accountability_check["days_until"]} dias.',
                    severity=Severity.MEDIUM if accountability_check['days_until'] > 30 else Severity.HIGH,
                    category='accountability',
                    project_id=project.id,
                    project_name=project.title
                ))

        if audit_ncs:
            open_audit = [nc for nc in audit_ncs if nc.status != 'Fechada']
            if open_audit:
                insights.append(self.create_insight(
                    title=f'{len(open_audit)} finding(s) de auditoria aberto(s)',
                    description=f'Não conformidades de auditoria pendentes em {project.title}.',
                    severity=Severity.HIGH,
                    category='audit',
                    project_id=project.id,
                    project_name=project.title,
                    metric_name='audit_findings',
                    metric_value=len(open_audit)
                ))

        regulatory_ncs = [nc for nc in open_ncs if nc.nc_type == 'Regulatório']
        if regulatory_ncs:
            insights.append(self.create_insight(
                title=f'{len(regulatory_ncs)} NC regulatória(s)',
                description='Não conformidades regulatórias requerem atenção prioritária.',
                severity=Severity.CRITICAL,
                category='regulatory',
                project_id=project.id,
                project_name=project.title
            ))

        return {
            'project_id': project.id,
            'project_name': project.title,
            'nc_count': len(ncs),
            'open_nc': len(open_ncs),
            'audit_findings': len([nc for nc in audit_ncs if nc.status != 'Fechada']),
            'evidence_missing': evidence_missing,
            'doc_gaps': doc_gaps,
            'is_funded': is_funded,
            'insights': insights,
            'actions': actions
        }

    def _is_funded_project(self, project) -> bool:
        """Check if project is funded by agencies requiring accountability."""
        funding_keywords = ['FINEP', 'EMBRAPII', 'FAPESP', 'FAPESC', 'CNPq', 'BNDES', 'Lei do Bem']
        if project.description:
            for keyword in funding_keywords:
                if keyword.lower() in project.description.lower():
                    return True
        if project.funding_source:
            return True
        return False

    def _has_evidence(self, milestone) -> bool:
        """Check if milestone has evidence documented."""
        if hasattr(milestone, 'evidence') and milestone.evidence:
            return True
        if hasattr(milestone, 'attachments') and milestone.attachments:
            return True
        return milestone.progress == 100

    def _has_documentation(self, expense) -> bool:
        """Check if expense has proper documentation."""
        if hasattr(expense, 'invoice_number') and expense.invoice_number:
            return True
        if hasattr(expense, 'attachment') and expense.attachment:
            return True
        return False

    def _check_accountability_deadlines(self, project) -> Dict:
        """Check upcoming accountability deadlines."""
        today = date.today()

        if project.end_date:
            days_until = (project.end_date - today).days + 60
            return {
                'due_soon': days_until <= 90,
                'days_until': days_until
            }
        return {'due_soon': False, 'days_until': 999}

    def _calculate_compliance_score(self, metrics: Dict) -> float:
        """Calculate overall compliance score."""
        score = 100

        score -= metrics['open_nc'] * 3
        score -= metrics['evidence_missing'] * 5
        score -= metrics['documentation_gaps'] * 4
        score -= metrics.get('audit_findings', 0) * 10

        return max(0, min(100, score))

    def _analyze_portfolio_compliance(self, metrics: Dict) -> List[Insight]:
        """Analyze portfolio-level compliance status."""
        insights = []

        score = metrics['compliance_score']

        if score >= 90:
            insights.append(self.create_insight(
                title=f'Compliance Score: {score:.0f}/100',
                description='Portfolio em conformidade com boas práticas de governança.',
                severity=Severity.INFO,
                category='compliance_score'
            ))
        elif score >= 70:
            insights.append(self.create_insight(
                title=f'Compliance Score: {score:.0f}/100',
                description='Portfolio requer atenção em alguns aspectos de compliance.',
                severity=Severity.MEDIUM,
                category='compliance_score'
            ))
        else:
            insights.append(self.create_insight(
                title=f'Compliance Score Crítico: {score:.0f}/100',
                description='Riscos significativos de compliance identificados.',
                severity=Severity.CRITICAL,
                category='compliance_score',
                recommendation='Ação imediata necessária para regularização.'
            ))

        return insights

    def _generate_summary(self, metrics: Dict, status: HealthStatus) -> str:
        """Generate executive summary."""
        score = metrics['compliance_score']
        nc = metrics['open_nc']
        evidence = metrics['evidence_missing']
        docs = metrics['documentation_gaps']

        if status == HealthStatus.CRITICAL:
            return f"🔴 Compliance crítico ({score:.0f}/100). {nc} NC abertas, {evidence} evidências faltantes."
        elif status == HealthStatus.ATTENTION:
            return f"🟡 Compliance em atenção ({score:.0f}/100). {docs} gap(s) de documentação."
        else:
            return f"🟢 Compliance saudável ({score:.0f}/100). Governança em dia."
