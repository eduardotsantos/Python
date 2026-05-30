"""
Resource Agent - Monitors team capacity and allocation.
Analyzes: Capacity, allocation, available hours, overload.
"""
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict
from .base import (
    BaseAgent, AgentResult, Insight, ActionSuggestion,
    Severity, HealthStatus, ActionType
)


class ResourceAgent(BaseAgent):
    """
    Agente de Recursos.
    Monitors team capacity, allocation percentages, and workload balance.
    """

    @property
    def name(self) -> str:
        return 'resource_agent'

    @property
    def display_name(self) -> str:
        return 'Agente de Recursos'

    @property
    def description(self) -> str:
        return 'Monitora capacidade, alocação, horas e sobrecarga de equipes'

    @property
    def icon(self) -> str:
        return 'bi-people'

    @property
    def color(self) -> str:
        return 'primary'

    def analyze(self, project_id: Optional[int] = None) -> AgentResult:
        self._start_execution()

        from models import Resource, MilestoneResource, Milestone, Project

        insights = []
        actions = []
        metrics = {
            'total_resources': 0,
            'overloaded': 0,
            'underutilized': 0,
            'optimal': 0,
            'resource_details': [],
            'avg_utilization': 0
        }

        resource_allocations = self._calculate_resource_allocations(project_id)
        metrics['total_resources'] = len(resource_allocations)

        utilization_sum = 0
        for resource_id, data in resource_allocations.items():
            utilization = data['total_allocation']
            utilization_sum += utilization

            status = 'optimal'
            if utilization > 100:
                status = 'overloaded'
                metrics['overloaded'] += 1
            elif utilization < 50:
                status = 'underutilized'
                metrics['underutilized'] += 1
            else:
                metrics['optimal'] += 1

            metrics['resource_details'].append({
                'resource_id': resource_id,
                'name': data['name'],
                'utilization': utilization,
                'status': status,
                'projects': data['projects']
            })

            if utilization > 100:
                severity = Severity.CRITICAL if utilization > 130 else Severity.HIGH
                insights.append(self.create_insight(
                    title=f'{data["name"]} com sobrecarga: {utilization:.0f}%',
                    description=f'Recurso alocado em {len(data["projects"])} projeto(s). Excesso de {utilization - 100:.0f}%.',
                    severity=severity,
                    category='overload',
                    metric_name='utilization',
                    metric_value=utilization,
                    metric_threshold=100,
                    recommendation='Redistribuir atividades ou adicionar recursos de apoio.',
                    data={'resource_id': resource_id, 'projects': list(data['projects'].keys())}
                ))

                actions.append(self.suggest_action(
                    action_type=ActionType.REALLOCATE_RESOURCE,
                    title=f'Redistribuir carga de {data["name"]}',
                    description=f'Recurso com {utilization:.0f}% de alocação precisa de redistribuição.',
                    priority=severity,
                    data={'resource_id': resource_id, 'current_utilization': utilization}
                ))

        if metrics['total_resources'] > 0:
            metrics['avg_utilization'] = utilization_sum / metrics['total_resources']

        team_insights = self._analyze_team_balance(metrics)
        insights.extend(team_insights)

        overall_status = HealthStatus.HEALTHY
        if metrics['overloaded'] > 0:
            if any(r['utilization'] > 130 for r in metrics['resource_details']):
                overall_status = HealthStatus.CRITICAL
            else:
                overall_status = HealthStatus.ATTENTION
        elif metrics['underutilized'] > metrics['total_resources'] * 0.3:
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

    def _calculate_resource_allocations(self, project_id: Optional[int] = None) -> Dict:
        """Calculate total allocation per resource across projects."""
        from models import Resource, MilestoneResource, Milestone, Project

        resource_query = Resource.query.filter_by(tenant_id=self.tenant_id, type='Pessoa', status='Ativo')
        resources = resource_query.all()

        allocations = {}
        for resource in resources:
            allocations[resource.id] = {
                'name': resource.name,
                'total_allocation': 0,
                'projects': {}
            }

            milestone_resources = MilestoneResource.query.filter_by(resource_id=resource.id).all()

            for mr in milestone_resources:
                milestone = Milestone.query.get(mr.milestone_id)
                if not milestone or milestone.status == 'Concluído':
                    continue

                project = Project.query.get(milestone.project_id)
                if not project or project.status not in ['Em Andamento', 'Planejamento']:
                    continue

                if project_id and project.id != project_id:
                    continue

                allocation_pct = mr.allocation_percentage or 0
                allocations[resource.id]['total_allocation'] += allocation_pct

                if project.id not in allocations[resource.id]['projects']:
                    allocations[resource.id]['projects'][project.id] = {
                        'name': project.title,
                        'allocation': 0
                    }
                allocations[resource.id]['projects'][project.id]['allocation'] += allocation_pct

        return allocations

    def _analyze_team_balance(self, metrics: Dict) -> List[Insight]:
        """Analyze overall team workload balance."""
        insights = []

        total = metrics['total_resources']
        if total == 0:
            return insights

        overloaded_pct = (metrics['overloaded'] / total) * 100
        underutilized_pct = (metrics['underutilized'] / total) * 100

        if overloaded_pct > 30:
            insights.append(self.create_insight(
                title=f'{overloaded_pct:.0f}% da equipe sobrecarregada',
                description=f'{metrics["overloaded"]} de {total} recursos com mais de 100% de alocação.',
                severity=Severity.HIGH,
                category='team_balance',
                recommendation='Revisar distribuição de trabalho ou contratar recursos adicionais.'
            ))

        if underutilized_pct > 30:
            insights.append(self.create_insight(
                title=f'{underutilized_pct:.0f}% da equipe subutilizada',
                description=f'{metrics["underutilized"]} recursos com menos de 50% de alocação.',
                severity=Severity.MEDIUM,
                category='team_balance',
                recommendation='Considerar realocação para projetos com necessidade.'
            ))

        avg_util = metrics['avg_utilization']
        if 70 <= avg_util <= 90:
            insights.append(self.create_insight(
                title='Utilização média saudável',
                description=f'Média de utilização em {avg_util:.0f}% - dentro da faixa ideal (70-90%).',
                severity=Severity.INFO,
                category='team_balance'
            ))
        elif avg_util > 100:
            insights.append(self.create_insight(
                title='Equipe acima da capacidade',
                description=f'Média de utilização em {avg_util:.0f}% - acima da capacidade sustentável.',
                severity=Severity.HIGH,
                category='capacity'
            ))

        return insights

    def _generate_summary(self, metrics: Dict, status: HealthStatus) -> str:
        """Generate executive summary."""
        total = metrics['total_resources']
        overloaded = metrics['overloaded']
        avg = metrics['avg_utilization']

        if status == HealthStatus.CRITICAL:
            return f"🔴 {overloaded} recurso(s) com sobrecarga crítica (>130%). Média: {avg:.0f}%."
        elif status == HealthStatus.ATTENTION:
            return f"🟡 {overloaded} recurso(s) sobrecarregado(s). Utilização média: {avg:.0f}%."
        else:
            return f"🟢 Equipe balanceada. {total} recursos com utilização média de {avg:.0f}%."

    def suggest_reallocation(self, resource_id: int) -> Dict:
        """Suggest reallocation options for overloaded resource."""
        from models import Resource, MilestoneResource, Milestone, Project

        resource = Resource.query.get(resource_id)
        if not resource:
            return {}

        allocations = self._calculate_resource_allocations()
        if resource_id not in allocations:
            return {}

        data = allocations[resource_id]
        current_util = data['total_allocation']

        available_resources = []
        for rid, rdata in allocations.items():
            if rid != resource_id and rdata['total_allocation'] < 80:
                available_resources.append({
                    'id': rid,
                    'name': rdata['name'],
                    'current_utilization': rdata['total_allocation'],
                    'available_capacity': 100 - rdata['total_allocation']
                })

        available_resources.sort(key=lambda x: x['available_capacity'], reverse=True)

        suggestions = []
        excess = current_util - 100

        for ar in available_resources[:3]:
            transfer = min(excess, ar['available_capacity'])
            suggestions.append({
                'target_resource': ar['name'],
                'transfer_percentage': transfer,
                'resulting_utilization': {
                    'source': current_util - transfer,
                    'target': ar['current_utilization'] + transfer
                }
            })

        return {
            'resource': resource.name,
            'current_utilization': current_util,
            'excess': excess,
            'suggestions': suggestions
        }
