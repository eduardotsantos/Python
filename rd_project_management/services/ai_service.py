"""
AI Service for R&D Project Management System.
Provides AI-powered features using Claude API.
"""
import os
import json
import logging
from datetime import datetime, date
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)


def get_anthropic_client():
    """Get Anthropic client, returns None if not configured."""
    try:
        from anthropic import Anthropic
        api_key = os.environ.get('ANTHROPIC_API_KEY')
        if not api_key:
            logger.warning("ANTHROPIC_API_KEY not configured")
            return None
        return Anthropic(api_key=api_key)
    except ImportError:
        logger.warning("anthropic package not installed")
        return None


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text content from a PDF file."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text.strip()
    except ImportError:
        logger.warning("PyMuPDF not installed, trying pdfplumber")
        try:
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                text = ""
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            return text.strip()
        except ImportError:
            logger.error("No PDF library available (install PyMuPDF or pdfplumber)")
            return ""
    except Exception as e:
        logger.error(f"Error extracting PDF text: {e}")
        return ""


def analyze_public_call(document_text: str) -> Optional[Dict[str, Any]]:
    """
    Analyze a public call document and extract key information.
    Returns structured data about the call.
    """
    client = get_anthropic_client()
    if not client:
        return None

    prompt = f"""Analise este edital/chamada pública de P&D e extraia as seguintes informações em formato JSON:

{{
    "titulo": "título do edital",
    "orgao": "órgão/agência responsável",
    "prazo_submissao": "data limite para submissão",
    "valor_maximo": "valor máximo do financiamento (número ou null)",
    "valor_minimo": "valor mínimo do financiamento (número ou null)",
    "areas_tematicas": ["lista de áreas temáticas"],
    "requisitos_elegibilidade": ["lista de requisitos para participar"],
    "itens_financiaveis": ["lista de itens que podem ser financiados"],
    "contrapartida": "informação sobre contrapartida exigida",
    "duracao_projeto": "duração máxima/mínima do projeto",
    "documentos_necessarios": ["lista de documentos para submissão"],
    "contato": "informações de contato",
    "resumo": "resumo executivo do edital em 3-4 frases",
    "pontos_atencao": ["pontos críticos a serem observados"]
}}

Se alguma informação não estiver disponível, use null.

EDITAL:
{document_text[:15000]}
"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )

        # Extract JSON from response
        response_text = response.content[0].text

        # Try to find JSON in the response
        start = response_text.find('{')
        end = response_text.rfind('}') + 1
        if start != -1 and end > start:
            json_str = response_text[start:end]
            return json.loads(json_str)

        return {"error": "Could not parse response", "raw": response_text}

    except Exception as e:
        logger.error(f"Error analyzing public call: {e}")
        return {"error": str(e)}


def match_project_to_calls(project: Dict[str, Any], calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Match a project to available public calls.
    Returns calls ranked by compatibility with scores and recommendations.
    """
    client = get_anthropic_client()
    if not client:
        return []

    project_info = f"""
PROJETO:
- Título: {project.get('title', 'N/A')}
- Descrição: {project.get('description', 'N/A')}
- Categoria: {project.get('category', 'N/A')}
- Orçamento: R$ {project.get('budget', 0):,.2f}
- Data Início: {project.get('start_date', 'N/A')}
- Data Fim: {project.get('end_date', 'N/A')}
- Fonte de Financiamento: {project.get('funding_source', 'N/A')}
"""

    calls_info = "\nCHAMADAS PÚBLICAS DISPONÍVEIS:\n"
    for i, call in enumerate(calls[:10], 1):  # Limit to 10 calls
        calls_info += f"""
{i}. ID: {call.get('id')}
   Título: {call.get('title', 'N/A')}
   Fonte: {call.get('source', 'N/A')}
   Tema: {call.get('theme', 'N/A')}
   Descrição: {call.get('description', 'N/A')[:300] if call.get('description') else 'N/A'}
   Prazo: {call.get('deadline', 'N/A')}
   Público-alvo: {call.get('target_audience', 'N/A')}
"""

    prompt = f"""Analise a compatibilidade entre o projeto e as chamadas públicas disponíveis.

{project_info}
{calls_info}

Para cada chamada compatível, retorne um JSON array com:
{{
    "matches": [
        {{
            "call_id": <id da chamada>,
            "score": <0-100 score de compatibilidade>,
            "justificativa": "por que é compatível",
            "adaptacoes_necessarias": ["lista de adaptações para o projeto se candidatar"],
            "pontos_fortes": ["pontos fortes do projeto para esta chamada"],
            "riscos": ["possíveis riscos ou desafios"]
        }}
    ]
}}

Ordene por score decrescente. Inclua apenas chamadas com score >= 40.
"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = response.content[0].text
        start = response_text.find('{')
        end = response_text.rfind('}') + 1
        if start != -1 and end > start:
            result = json.loads(response_text[start:end])
            return result.get('matches', [])

        return []

    except Exception as e:
        logger.error(f"Error matching project to calls: {e}")
        return []


def generate_project_report(project: Dict[str, Any], report_type: str = "parcial") -> Optional[str]:
    """
    Generate a project report (partial or final).
    """
    client = get_anthropic_client()
    if not client:
        return None

    expenses_info = ""
    if project.get('expenses'):
        expenses_info = "\nDESPESAS:\n"
        total_expenses = 0
        for exp in project['expenses']:
            expenses_info += f"- {exp['description']}: R$ {exp['amount']:,.2f} ({exp['category']}) - {exp['date']}\n"
            total_expenses += exp['amount']
        expenses_info += f"Total: R$ {total_expenses:,.2f}\n"

    milestones_info = ""
    if project.get('milestones'):
        milestones_info = "\nMARCOS/METAS:\n"
        for m in project['milestones']:
            milestones_info += f"- {m['title']}: {m['progress']}% ({m['status']})\n"

    timesheets_info = ""
    total_hours = 0
    if project.get('timesheets'):
        for ts in project['timesheets']:
            total_hours += ts['hours']
        timesheets_info = f"\nHORAS TRABALHADAS: {total_hours:.1f} horas\n"

    resources_info = ""
    if project.get('resources'):
        resources_info = "\nRECURSOS:\n"
        for r in project['resources']:
            resources_info += f"- {r['name']} ({r['type']}): {r.get('hours_allocated', 0)} horas alocadas\n"

    report_type_text = "PARCIAL" if report_type == "parcial" else "FINAL"

    prompt = f"""Gere um relatório técnico {report_type_text} para o seguinte projeto de P&D:

PROJETO:
- Código: {project.get('code', 'N/A')}
- Título: {project.get('title', 'N/A')}
- Descrição: {project.get('description', 'N/A')}
- Status: {project.get('status', 'N/A')}
- Categoria: {project.get('category', 'N/A')}
- Período: {project.get('start_date', 'N/A')} a {project.get('end_date', 'N/A')}
- Orçamento: R$ {project.get('budget', 0):,.2f}
- Fonte de Financiamento: {project.get('funding_source', 'N/A')}
{expenses_info}
{milestones_info}
{timesheets_info}
{resources_info}

Gere um relatório técnico profissional em português com as seguintes seções:

1. RESUMO EXECUTIVO
2. OBJETIVOS DO PROJETO
3. METODOLOGIA E ATIVIDADES REALIZADAS
4. RESULTADOS ALCANÇADOS
5. EXECUÇÃO FINANCEIRA
6. EQUIPE E RECURSOS
7. CRONOGRAMA E MARCOS
8. DIFICULDADES ENCONTRADAS E SOLUÇÕES
9. {"PRÓXIMAS ETAPAS" if report_type == "parcial" else "CONCLUSÕES E IMPACTOS"}
10. CONSIDERAÇÕES FINAIS

Use formatação markdown. Seja profissional e objetivo.
"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}]
        )

        return response.content[0].text

    except Exception as e:
        logger.error(f"Error generating report: {e}")
        return None


def analyze_project_risks(project: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Analyze project risks based on current data.
    """
    client = get_anthropic_client()
    if not client:
        return None

    # Calculate metrics
    total_budget = project.get('budget', 0) or 0
    total_spent = sum(e.get('amount', 0) for e in project.get('expenses', []))
    budget_used_pct = (total_spent / total_budget * 100) if total_budget > 0 else 0

    # Calculate time progress
    start_date = project.get('start_date')
    end_date = project.get('end_date')
    time_elapsed_pct = 0
    days_remaining = 0

    if start_date and end_date:
        try:
            if isinstance(start_date, str):
                start = datetime.strptime(start_date, '%Y-%m-%d').date()
            else:
                start = start_date
            if isinstance(end_date, str):
                end = datetime.strptime(end_date, '%Y-%m-%d').date()
            else:
                end = end_date

            total_days = (end - start).days
            elapsed_days = (date.today() - start).days
            days_remaining = (end - date.today()).days
            time_elapsed_pct = (elapsed_days / total_days * 100) if total_days > 0 else 0
        except Exception:
            pass

    # Calculate milestone progress
    milestones = project.get('milestones', [])
    avg_milestone_progress = 0
    if milestones:
        avg_milestone_progress = sum(m.get('progress', 0) for m in milestones) / len(milestones)

    delayed_milestones = []
    for m in milestones:
        end_str = m.get('end_date')
        if end_str:
            try:
                if isinstance(end_str, str):
                    m_end = datetime.strptime(end_str, '%Y-%m-%d').date()
                else:
                    m_end = end_str
                if m_end < date.today() and m.get('progress', 0) < 100:
                    delayed_milestones.append(m.get('title', 'N/A'))
            except Exception:
                pass

    metrics = f"""
MÉTRICAS DO PROJETO:
- Título: {project.get('title', 'N/A')}
- Status: {project.get('status', 'N/A')}
- Orçamento Total: R$ {total_budget:,.2f}
- Gasto Atual: R$ {total_spent:,.2f}
- % Orçamento Utilizado: {budget_used_pct:.1f}%
- % Tempo Decorrido: {time_elapsed_pct:.1f}%
- Dias Restantes: {days_remaining}
- Progresso Médio dos Marcos: {avg_milestone_progress:.1f}%
- Marcos Atrasados: {len(delayed_milestones)} ({', '.join(delayed_milestones) if delayed_milestones else 'Nenhum'})
- Total de Despesas Registradas: {len(project.get('expenses', []))}
- Total de Recursos Alocados: {len(project.get('resources', []))}
"""

    prompt = f"""Analise os riscos do seguinte projeto de P&D e forneça uma análise detalhada.

{metrics}

Retorne um JSON com a seguinte estrutura:
{{
    "nivel_risco_geral": "baixo|médio|alto|crítico",
    "score_risco": <0-100>,
    "riscos_identificados": [
        {{
            "categoria": "orçamento|cronograma|escopo|recursos|qualidade",
            "descricao": "descrição do risco",
            "severidade": "baixa|média|alta|crítica",
            "probabilidade": "baixa|média|alta",
            "impacto": "descrição do impacto potencial",
            "mitigacao": "ação recomendada para mitigar"
        }}
    ],
    "alertas": ["lista de alertas imediatos"],
    "recomendacoes": ["lista de recomendações gerais"],
    "previsao_conclusao": {{
        "status": "no_prazo|atrasado|em_risco",
        "estimativa": "estimativa de conclusão baseada nos dados",
        "confianca": "baixa|média|alta"
    }},
    "burn_rate": {{
        "mensal": <gasto médio mensal estimado>,
        "projecao_final": <projeção de gasto total>,
        "status": "dentro_orcamento|em_risco|acima_orcamento"
    }}
}}
"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = response.content[0].text
        start = response_text.find('{')
        end = response_text.rfind('}') + 1
        if start != -1 and end > start:
            return json.loads(response_text[start:end])

        return {"error": "Could not parse response"}

    except Exception as e:
        logger.error(f"Error analyzing risks: {e}")
        return {"error": str(e)}


def chat_assistant(message: str, context: Dict[str, Any], conversation_history: List[Dict] = None) -> str:
    """
    AI Chat assistant for the project management system.
    """
    client = get_anthropic_client()
    if not client:
        return "Desculpe, o assistente de IA não está configurado. Configure a variável ANTHROPIC_API_KEY."

    system_prompt = f"""Você é um assistente de IA especializado em gestão de projetos de P&D (Pesquisa e Desenvolvimento).
Você tem acesso às seguintes informações do sistema:

CONTEXTO DO USUÁRIO:
- Nome: {context.get('user_name', 'Usuário')}
- Empresa: {context.get('tenant_name', 'N/A')}
- Função: {context.get('user_role', 'N/A')}

RESUMO DOS PROJETOS:
{context.get('projects_summary', 'Nenhum projeto cadastrado')}

RESUMO DAS CHAMADAS PÚBLICAS:
{context.get('calls_summary', 'Nenhuma chamada cadastrada')}

RESUMO FINANCEIRO:
{context.get('financial_summary', 'Sem dados financeiros')}

Responda de forma clara, objetiva e profissional em português.
Se o usuário perguntar sobre dados que você não tem, indique que não tem acesso a essa informação específica.
Você pode fazer cálculos, análises e dar recomendações baseadas nos dados disponíveis.
"""

    messages = []

    # Add conversation history if available
    if conversation_history:
        for msg in conversation_history[-10:]:  # Keep last 10 messages
            messages.append({"role": msg['role'], "content": msg['content']})

    messages.append({"role": "user", "content": message})

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            system=system_prompt,
            messages=messages
        )

        return response.content[0].text

    except Exception as e:
        logger.error(f"Error in chat assistant: {e}")
        return f"Desculpe, ocorreu um erro ao processar sua mensagem: {str(e)}"


def get_system_context(tenant_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Get system context for the AI assistant.
    """
    from models import Project, PublicCall, Expense
    from sqlalchemy import func

    context = {
        'projects_summary': '',
        'calls_summary': '',
        'financial_summary': ''
    }

    try:
        # Projects summary
        projects_query = Project.query
        if tenant_id:
            projects_query = projects_query.filter_by(tenant_id=tenant_id)

        projects = projects_query.all()
        if projects:
            summary_lines = [f"Total de projetos: {len(projects)}"]
            status_counts = {}
            total_budget = 0
            for p in projects:
                status_counts[p.status] = status_counts.get(p.status, 0) + 1
                total_budget += p.budget or 0

            for status, count in status_counts.items():
                summary_lines.append(f"- {status}: {count} projetos")
            summary_lines.append(f"Orçamento total: R$ {total_budget:,.2f}")

            context['projects_summary'] = '\n'.join(summary_lines)

        # Calls summary
        calls_query = PublicCall.query.filter(
            (PublicCall.tenant_id == tenant_id) | (PublicCall.tenant_id.is_(None))
        )
        calls = calls_query.filter_by(status='Aberta').all()
        if calls:
            context['calls_summary'] = f"Chamadas abertas: {len(calls)}"

        # Financial summary
        if tenant_id:
            expenses = Expense.query.filter_by(tenant_id=tenant_id).all()
            if expenses:
                total_expenses = sum(e.amount for e in expenses)
                context['financial_summary'] = f"Total de despesas: R$ {total_expenses:,.2f}"

    except Exception as e:
        logger.error(f"Error getting system context: {e}")

    return context
