"""
Minutes Reader Agent - Parses meeting minutes to extract actionable items.
Automatically creates: Pending items, Risks, Non-conformities, Actions.
"""
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Tuple
import re
from .base import (
    BaseAgent, AgentResult, Insight, ActionSuggestion,
    Severity, HealthStatus, ActionType
)


class MinutesReaderAgent(BaseAgent):
    """
    Agente Leitor de Atas.
    Parses meeting minutes and extracts actionable items automatically.
    """

    @property
    def name(self) -> str:
        return 'minutes_reader'

    @property
    def display_name(self) -> str:
        return 'Agente Leitor de Atas'

    @property
    def description(self) -> str:
        return 'Analisa atas de reunião e extrai pendências, riscos e ações automaticamente'

    @property
    def icon(self) -> str:
        return 'bi-file-earmark-text'

    @property
    def color(self) -> str:
        return 'secondary'

    PENDING_PATTERNS = [
        (r'(\w+)\s+(?:deverá|deve|irá|vai|ficou responsável por)\s+(.+?)(?:até|para)\s+(\d{1,2}/\d{1,2}(?:/\d{2,4})?)', 'pending_with_date'),
        (r'(\w+)\s+(?:deverá|deve|irá|vai|ficou responsável por)\s+(.+?)(?:\.|;|$)', 'pending_no_date'),
        (r'(?:ficou definido que|ficou acordado que)\s+(\w+)\s+(.+?)(?:\.|;|$)', 'decision'),
        (r'(?:necessário|precisa|precisamos)\s+(.+?)(?:\.|;|$)', 'need'),
        (r'(?:pendente:|pendência:)\s*(.+?)(?:\.|;|$)', 'explicit_pending'),
    ]

    RISK_PATTERNS = [
        (r'(?:existe risco de|há risco de|risco identificado:?)\s+(.+?)(?:\.|;|$)', 'risk_explicit'),
        (r'(?:pode atrasar|pode impactar|pode prejudicar)\s+(.+?)(?:\.|;|$)', 'risk_implicit'),
        (r'(?:preocupação com|preocupante)\s+(.+?)(?:\.|;|$)', 'concern'),
    ]

    NC_PATTERNS = [
        (r'(?:não foi apresentad[oa]|não foi entregue|faltou)\s+(.+?)(?:\.|;|$)', 'nc_missing'),
        (r'(?:não conformidade:?|nc:?)\s+(.+?)(?:\.|;|$)', 'nc_explicit'),
        (r'(?:problema identificado:?|erro identificado:?)\s+(.+?)(?:\.|;|$)', 'nc_problem'),
        (r'(?:violação de|descumprimento de)\s+(.+?)(?:\.|;|$)', 'nc_violation'),
    ]

    ACTION_PATTERNS = [
        (r'(?:ação:?|ação corretiva:?)\s+(.+?)(?:\.|;|$)', 'action_explicit'),
        (r'(?:será implementad[oa]|implementar)\s+(.+?)(?:\.|;|$)', 'action_implement'),
        (r'(?:corrigir|resolver|solucionar)\s+(.+?)(?:\.|;|$)', 'action_fix'),
    ]

    def analyze(self, project_id: Optional[int] = None) -> AgentResult:
        self._start_execution()

        insights = []
        actions = []
        metrics = {
            'minutes_analyzed': 0,
            'pending_extracted': 0,
            'risks_extracted': 0,
            'nc_extracted': 0,
            'actions_extracted': 0
        }

        from models import MeetingMinutes, Project

        query = MeetingMinutes.query
        if project_id:
            query = query.filter_by(project_id=project_id)
        else:
            query = query.join(Project).filter(Project.tenant_id == self.tenant_id)

        recent_minutes = query.filter(
            MeetingMinutes.meeting_date >= date.today() - timedelta(days=30)
        ).all()

        metrics['minutes_analyzed'] = len(recent_minutes)

        for minutes in recent_minutes:
            extractions = self.parse_minutes(minutes)

            for pending in extractions['pending']:
                metrics['pending_extracted'] += 1
                actions.append(self.suggest_action(
                    action_type=ActionType.CREATE_PENDING,
                    title=f'Criar pendência: {pending["title"][:50]}',
                    description=pending['description'],
                    priority=Severity.MEDIUM,
                    project_id=minutes.project_id,
                    data={
                        'title': pending['title'],
                        'responsible': pending.get('responsible'),
                        'due_date': pending.get('due_date'),
                        'source': f'Ata de {minutes.meeting_date}'
                    },
                    auto_executable=True
                ))

            for risk in extractions['risks']:
                metrics['risks_extracted'] += 1
                actions.append(self.suggest_action(
                    action_type=ActionType.CREATE_RISK,
                    title=f'Criar risco: {risk["title"][:50]}',
                    description=risk['description'],
                    priority=Severity.HIGH,
                    project_id=minutes.project_id,
                    data={
                        'title': risk['title'],
                        'source': f'Ata de {minutes.meeting_date}'
                    },
                    auto_executable=True
                ))

            for nc in extractions['nc']:
                metrics['nc_extracted'] += 1
                actions.append(self.suggest_action(
                    action_type=ActionType.CREATE_NC,
                    title=f'Criar NC: {nc["title"][:50]}',
                    description=nc['description'],
                    priority=Severity.HIGH,
                    project_id=minutes.project_id,
                    data={
                        'title': nc['title'],
                        'source': f'Ata de {minutes.meeting_date}'
                    },
                    auto_executable=True
                ))

            for action_item in extractions['actions']:
                metrics['actions_extracted'] += 1
                actions.append(self.suggest_action(
                    action_type=ActionType.CREATE_ACTION,
                    title=f'Criar ação: {action_item["title"][:50]}',
                    description=action_item['description'],
                    priority=Severity.MEDIUM,
                    project_id=minutes.project_id,
                    data={
                        'description': action_item['title'],
                        'source': f'Ata de {minutes.meeting_date}'
                    },
                    auto_executable=True
                ))

        total_extracted = (
            metrics['pending_extracted'] + metrics['risks_extracted'] +
            metrics['nc_extracted'] + metrics['actions_extracted']
        )

        if total_extracted > 0:
            insights.append(self.create_insight(
                title=f'{total_extracted} itens extraídos de {metrics["minutes_analyzed"]} ata(s)',
                description=(
                    f'{metrics["pending_extracted"]} pendências, '
                    f'{metrics["risks_extracted"]} riscos, '
                    f'{metrics["nc_extracted"]} NCs, '
                    f'{metrics["actions_extracted"]} ações.'
                ),
                severity=Severity.INFO,
                category='extraction_summary'
            ))

        overall_status = HealthStatus.HEALTHY
        if metrics['risks_extracted'] > 0 or metrics['nc_extracted'] > 0:
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

    def parse_minutes(self, minutes) -> Dict[str, List]:
        """Parse a single meeting minutes document."""
        if not hasattr(minutes, 'content') or not minutes.content:
            return {'pending': [], 'risks': [], 'nc': [], 'actions': []}

        content = minutes.content

        pending = self._extract_pending(content)
        risks = self._extract_risks(content)
        nc = self._extract_nc(content)
        actions = self._extract_actions(content)

        return {
            'pending': pending,
            'risks': risks,
            'nc': nc,
            'actions': actions
        }

    def _extract_pending(self, content: str) -> List[Dict]:
        """Extract pending items from content."""
        pending = []

        for pattern, pattern_type in self.PENDING_PATTERNS:
            matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)

            for match in matches:
                if pattern_type == 'pending_with_date':
                    responsible, task, due_date = match
                    pending.append({
                        'title': task.strip()[:200],
                        'description': f'Extraído automaticamente da ata. Responsável: {responsible}',
                        'responsible': responsible.strip(),
                        'due_date': self._parse_date(due_date),
                        'type': pattern_type
                    })
                elif pattern_type == 'pending_no_date':
                    responsible, task = match
                    pending.append({
                        'title': task.strip()[:200],
                        'description': f'Extraído automaticamente da ata. Responsável: {responsible}',
                        'responsible': responsible.strip(),
                        'type': pattern_type
                    })
                elif pattern_type in ['decision', 'need', 'explicit_pending']:
                    if isinstance(match, tuple):
                        text = ' '.join(match)
                    else:
                        text = match
                    if len(text.strip()) > 10:
                        pending.append({
                            'title': text.strip()[:200],
                            'description': 'Extraído automaticamente da ata.',
                            'type': pattern_type
                        })

        return pending[:10]

    def _extract_risks(self, content: str) -> List[Dict]:
        """Extract risks from content."""
        risks = []

        for pattern, pattern_type in self.RISK_PATTERNS:
            matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)

            for match in matches:
                text = match if isinstance(match, str) else match[0]
                if len(text.strip()) > 10:
                    risks.append({
                        'title': text.strip()[:200],
                        'description': f'Risco identificado em ata de reunião.',
                        'type': pattern_type
                    })

        return risks[:5]

    def _extract_nc(self, content: str) -> List[Dict]:
        """Extract non-conformities from content."""
        ncs = []

        for pattern, pattern_type in self.NC_PATTERNS:
            matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)

            for match in matches:
                text = match if isinstance(match, str) else match[0]
                if len(text.strip()) > 10:
                    ncs.append({
                        'title': text.strip()[:200],
                        'description': f'Não conformidade identificada em ata de reunião.',
                        'type': pattern_type
                    })

        return ncs[:5]

    def _extract_actions(self, content: str) -> List[Dict]:
        """Extract corrective actions from content."""
        actions = []

        for pattern, pattern_type in self.ACTION_PATTERNS:
            matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)

            for match in matches:
                text = match if isinstance(match, str) else match[0]
                if len(text.strip()) > 10:
                    actions.append({
                        'title': text.strip()[:200],
                        'description': f'Ação identificada em ata de reunião.',
                        'type': pattern_type
                    })

        return actions[:5]

    def _parse_date(self, date_str: str) -> Optional[str]:
        """Parse date string to ISO format."""
        try:
            parts = date_str.split('/')
            if len(parts) == 2:
                day, month = int(parts[0]), int(parts[1])
                year = date.today().year
                if month < date.today().month:
                    year += 1
                return f'{year}-{month:02d}-{day:02d}'
            elif len(parts) == 3:
                day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
                if year < 100:
                    year += 2000
                return f'{year}-{month:02d}-{day:02d}'
        except:
            pass
        return None

    def _generate_summary(self, metrics: Dict, status: HealthStatus) -> str:
        """Generate executive summary."""
        total = (
            metrics['pending_extracted'] + metrics['risks_extracted'] +
            metrics['nc_extracted'] + metrics['actions_extracted']
        )

        if total > 0:
            return f"📄 {total} item(ns) extraído(s) de {metrics['minutes_analyzed']} ata(s)."
        else:
            return f"📄 {metrics['minutes_analyzed']} ata(s) analisada(s). Nenhum item novo identificado."

    def parse_text(self, text: str, project_id: Optional[int] = None) -> Dict[str, List]:
        """Parse arbitrary text (for API usage)."""
        class FakeMinutes:
            def __init__(self, content, project_id):
                self.content = content
                self.project_id = project_id
                self.date = date.today()

        fake = FakeMinutes(text, project_id)
        return self.parse_minutes(fake)
