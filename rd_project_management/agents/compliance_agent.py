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

    def analyze_open_items(self, project_id: Optional[int] = None) -> AgentResult:
        """
        Analyze open bugs, NCs, and pending items.
        Suggests corrective actions based on time open and correlation with similar past items.
        """
        self._start_execution()

        from models import (Project, PendingItem, NonConformity, Bug,
                          CorrectiveAction, Risk)

        insights = []
        actions = []
        metrics = {
            'total_items_analyzed': 0,
            'items_needing_action': 0,
            'correlations_found': 0,
            'items_by_age': {'new': 0, 'medium': 0, 'old': 0, 'critical': 0}
        }
        today = date.today()

        query = Project.query.filter_by(tenant_id=self.tenant_id)
        if project_id:
            query = query.filter_by(id=project_id)
        else:
            query = query.filter(Project.status.in_(['Em Andamento', 'Planejamento']))

        projects = query.all()
        project_ids = [p.id for p in projects]

        # Get all open items
        open_pending = PendingItem.query.filter(
            PendingItem.project_id.in_(project_ids),
            PendingItem.status.notin_(['Concluída', 'Fechada', 'Resolvida', 'Cancelada'])
        ).all()

        open_bugs = Bug.query.filter(
            Bug.project_id.in_(project_ids),
            Bug.status.notin_(['Fechado', 'Resolvido', 'Encerrado'])
        ).all()

        open_ncs = NonConformity.query.filter(
            NonConformity.project_id.in_(project_ids),
            NonConformity.status.notin_(['Fechada', 'Encerrada', 'Resolvida'])
        ).all()

        # Get past resolved items for correlation
        resolved_pending = PendingItem.query.filter(
            PendingItem.tenant_id == self.tenant_id,
            PendingItem.status.in_(['Concluída', 'Fechada', 'Resolvida'])
        ).all()

        resolved_bugs = Bug.query.filter(
            Bug.tenant_id == self.tenant_id,
            Bug.status.in_(['Fechado', 'Resolvido', 'Encerrado'])
        ).all()

        resolved_ncs = NonConformity.query.filter(
            NonConformity.tenant_id == self.tenant_id,
            NonConformity.status.in_(['Fechada', 'Encerrada', 'Resolvida'])
        ).all()

        # Get corrective actions for correlation
        all_actions = CorrectiveAction.query.filter_by(tenant_id=self.tenant_id).all()

        # Analyze pending items
        for item in open_pending:
            metrics['total_items_analyzed'] += 1
            age_days = (today - item.created_at.date()).days if item.created_at else 0
            age_category = self._categorize_age(age_days)
            metrics['items_by_age'][age_category] += 1

            # Check if overdue
            is_overdue = item.due_date and item.due_date < today

            # Find correlation
            correlation = self._find_correlation(
                item.title, item.description or '',
                resolved_pending, all_actions, 'pending'
            )

            if age_days > 30 or is_overdue:
                metrics['items_needing_action'] += 1
                severity = Severity.CRITICAL if age_days > 60 or is_overdue else Severity.HIGH

                insight_desc = f"Pendência aberta há {age_days} dias"
                if is_overdue:
                    overdue_days = (today - item.due_date).days
                    insight_desc = f"Pendência atrasada há {overdue_days} dias (aberta há {age_days} dias)"

                insights.append(self.create_insight(
                    title=f"Pendência requer ação: {item.title[:50]}",
                    description=insight_desc,
                    severity=severity,
                    category='pending_aging',
                    project_id=item.project_id,
                    project_name=item.project.title if item.project else None,
                    metric_name='age_days',
                    metric_value=age_days
                ))

                # Suggest action
                action_desc = f"Resolver pendência '{item.title[:40]}' aberta há {age_days} dias."
                if correlation:
                    metrics['correlations_found'] += 1
                    action_desc += f"\n\n💡 Correlação encontrada: Item similar '{correlation['title'][:40]}' foi resolvido com a ação: {correlation['action'][:100]}"

                actions.append(self.suggest_action(
                    action_type=ActionType.CREATE_PENDING,
                    title=f"Ação corretiva para: {item.title[:40]}",
                    description=action_desc,
                    priority=severity,
                    project_id=item.project_id,
                    data={
                        'type': 'pending_resolution',
                        'item_id': item.id,
                        'correlation': correlation
                    }
                ))

        # Analyze bugs
        for bug in open_bugs:
            metrics['total_items_analyzed'] += 1
            age_days = (today - bug.reported_date).days if bug.reported_date else 0
            age_category = self._categorize_age(age_days)
            metrics['items_by_age'][age_category] += 1

            is_critical = bug.severity in ['Crítico', 'Crítica', 'Critical']

            correlation = self._find_correlation(
                bug.title, bug.description or '',
                resolved_bugs, all_actions, 'bug'
            )

            if age_days > 14 or is_critical:
                metrics['items_needing_action'] += 1
                severity = Severity.CRITICAL if is_critical or age_days > 30 else Severity.HIGH

                insights.append(self.create_insight(
                    title=f"Bug requer ação: {bug.title[:50]}",
                    description=f"Bug {bug.severity} aberto há {age_days} dias.",
                    severity=severity,
                    category='bug_aging',
                    project_id=bug.project_id,
                    project_name=bug.project.title if bug.project else None,
                    metric_name='age_days',
                    metric_value=age_days
                ))

                action_desc = f"Corrigir bug '{bug.title[:40]}' ({bug.severity}) aberto há {age_days} dias."
                if correlation:
                    metrics['correlations_found'] += 1
                    action_desc += f"\n\n💡 Correlação encontrada: Bug similar '{correlation['title'][:40]}' foi corrigido com: {correlation['action'][:100]}"

                actions.append(self.suggest_action(
                    action_type=ActionType.CREATE_PENDING,
                    title=f"Correção de bug: {bug.title[:40]}",
                    description=action_desc,
                    priority=severity,
                    project_id=bug.project_id,
                    data={
                        'type': 'bug_fix',
                        'item_id': bug.id,
                        'correlation': correlation
                    }
                ))

        # Analyze NCs
        for nc in open_ncs:
            metrics['total_items_analyzed'] += 1
            age_days = (today - nc.identified_date).days if nc.identified_date else 0
            age_category = self._categorize_age(age_days)
            metrics['items_by_age'][age_category] += 1

            is_severe = nc.impact in ['Alto', 'Crítico', 'High', 'Critical']

            correlation = self._find_correlation(
                nc.title, nc.description or '',
                resolved_ncs, all_actions, 'nc'
            )

            if age_days > 21 or is_severe:
                metrics['items_needing_action'] += 1
                severity = Severity.CRITICAL if is_severe or age_days > 45 else Severity.HIGH

                insights.append(self.create_insight(
                    title=f"NC requer ação: {nc.title[:50]}",
                    description=f"Não conformidade ({nc.nc_type}) aberta há {age_days} dias. Impacto: {nc.impact}",
                    severity=severity,
                    category='nc_aging',
                    project_id=nc.project_id,
                    project_name=nc.project.title if nc.project else None,
                    metric_name='age_days',
                    metric_value=age_days
                ))

                action_desc = f"Tratar NC '{nc.title[:40]}' ({nc.nc_type}) aberta há {age_days} dias."
                if nc.root_cause:
                    action_desc += f"\nCausa raiz identificada: {nc.root_cause[:100]}"
                if correlation:
                    metrics['correlations_found'] += 1
                    action_desc += f"\n\n💡 Correlação encontrada: NC similar '{correlation['title'][:40]}' foi tratada com: {correlation['action'][:100]}"

                actions.append(self.suggest_action(
                    action_type=ActionType.CREATE_PENDING,
                    title=f"Ação corretiva para NC: {nc.title[:40]}",
                    description=action_desc,
                    priority=severity,
                    project_id=nc.project_id,
                    data={
                        'type': 'nc_treatment',
                        'item_id': nc.id,
                        'correlation': correlation
                    }
                ))

        # Determine overall status
        if metrics['items_by_age']['critical'] > 0 or metrics['items_needing_action'] > 5:
            overall_status = HealthStatus.CRITICAL
        elif metrics['items_by_age']['old'] > 0 or metrics['items_needing_action'] > 0:
            overall_status = HealthStatus.ATTENTION
        else:
            overall_status = HealthStatus.HEALTHY

        summary = self._generate_items_summary(metrics, overall_status)

        return self.create_result(
            success=True,
            insights=insights,
            actions=actions,
            summary=summary,
            health_status=overall_status,
            metrics=metrics
        )

    def _categorize_age(self, days: int) -> str:
        """Categorize item age."""
        if days <= 7:
            return 'new'
        elif days <= 30:
            return 'medium'
        elif days <= 60:
            return 'old'
        else:
            return 'critical'

    def _find_correlation(self, title: str, description: str,
                         resolved_items: list, actions: list,
                         item_type: str) -> Optional[Dict]:
        """
        Find correlation with similar resolved items.
        Returns the action that was taken if a correlation is found.
        """
        title_lower = title.lower()
        desc_lower = description.lower() if description else ''

        # Extract key terms from title
        key_terms = [word for word in title_lower.split()
                    if len(word) > 3 and word not in ['para', 'com', 'que', 'não', 'the', 'for', 'and']]

        best_match = None
        best_score = 0

        for resolved in resolved_items:
            resolved_title = resolved.title.lower() if resolved.title else ''
            resolved_desc = (resolved.description or '').lower()

            # Calculate similarity score
            score = 0
            for term in key_terms:
                if term in resolved_title:
                    score += 3
                if term in resolved_desc:
                    score += 1

            if score > best_score and score >= 3:
                best_score = score
                best_match = resolved

        if best_match:
            # Find the corrective action associated with this item
            action_taken = None

            for action in actions:
                if item_type == 'pending' and action.pending_item_id == best_match.id:
                    action_taken = action.description
                    break
                elif item_type == 'bug' and action.bug_id == best_match.id:
                    action_taken = action.description
                    break
                elif item_type == 'nc' and action.non_conformity_id == best_match.id:
                    action_taken = action.description
                    break

            if not action_taken:
                # Use resolution notes if available
                if hasattr(best_match, 'resolution_notes') and best_match.resolution_notes:
                    action_taken = best_match.resolution_notes
                elif hasattr(best_match, 'corrective_plan') and best_match.corrective_plan:
                    action_taken = best_match.corrective_plan

            if action_taken:
                return {
                    'item_id': best_match.id,
                    'title': best_match.title,
                    'action': action_taken,
                    'similarity_score': best_score
                }

        return None

    def _generate_items_summary(self, metrics: Dict, status: HealthStatus) -> str:
        """Generate summary for open items analysis."""
        total = metrics['total_items_analyzed']
        needing = metrics['items_needing_action']
        correlations = metrics['correlations_found']
        ages = metrics['items_by_age']

        if status == HealthStatus.CRITICAL:
            return f"🔴 {total} itens analisados. {needing} requerem ação imediata ({ages['critical']} críticos). {correlations} correlações com itens anteriores encontradas."
        elif status == HealthStatus.ATTENTION:
            return f"🟡 {total} itens analisados. {needing} requerem atenção ({ages['old']} antigos). {correlations} correlações encontradas."
        else:
            return f"🟢 {total} itens analisados. Todos dentro do prazo esperado."
