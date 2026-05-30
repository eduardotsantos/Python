"""
Routes for Orion Autônomos PMO - AI Agent Dashboard and API.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date

from services.tenant_utils import tenant_required, get_current_tenant_id
from agents import PMOOrchestrator

pmo_agents_bp = Blueprint('pmo_agents', __name__, url_prefix='/pmo')


def get_orchestrator():
    """Get PMO Orchestrator for current tenant."""
    tenant_id = get_current_tenant_id()
    return PMOOrchestrator(tenant_id)


@pmo_agents_bp.route('/')
@login_required
@tenant_required
def dashboard():
    """Main PMO Agents dashboard."""
    orchestrator = get_orchestrator()
    agents_info = orchestrator.get_agent_info()

    return render_template('pmo_agents/dashboard.html',
        agents=agents_info,
        page_title='Orion Autônomos PMO'
    )


@pmo_agents_bp.route('/briefing')
@login_required
@tenant_required
def daily_briefing():
    """Generate and display daily executive briefing."""
    orchestrator = get_orchestrator()
    briefing = orchestrator.generate_daily_briefing(current_user.full_name)

    return render_template('pmo_agents/briefing.html',
        briefing=briefing,
        page_title='Briefing Executivo Diário'
    )


@pmo_agents_bp.route('/agent/<agent_name>')
@login_required
@tenant_required
def run_agent(agent_name):
    """Run a specific agent and show results."""
    project_id = request.args.get('project_id', type=int)

    orchestrator = get_orchestrator()
    agent = orchestrator.get_agent(agent_name)

    if not agent:
        flash('Agente não encontrado.', 'danger')
        return redirect(url_for('pmo_agents.dashboard'))

    result = orchestrator.run_agent(agent_name, project_id)

    return render_template('pmo_agents/agent_result.html',
        agent=agent,
        result=result,
        project_id=project_id,
        page_title=f'{agent.display_name} - Resultado'
    )


@pmo_agents_bp.route('/action-center')
@login_required
@tenant_required
def action_center():
    """Action center - view and execute suggested actions."""
    orchestrator = get_orchestrator()

    results = orchestrator.run_all_agents()

    all_actions = []
    for result in results:
        for action in result.actions:
            all_actions.append({
                'action': action,
                'agent_name': result.agent_name
            })

    all_actions.sort(key=lambda x: (
        0 if x['action'].priority.value == 'critical' else
        1 if x['action'].priority.value == 'high' else
        2 if x['action'].priority.value == 'medium' else 3
    ))

    return render_template('pmo_agents/action_center.html',
        actions=all_actions[:20],
        page_title='Central de Ações'
    )


@pmo_agents_bp.route('/minutes-parser', methods=['GET', 'POST'])
@login_required
@tenant_required
def minutes_parser():
    """Parse meeting minutes text."""
    from models import Project

    tenant_id = get_current_tenant_id()
    projects = Project.query.filter_by(tenant_id=tenant_id).all()

    extractions = None
    if request.method == 'POST':
        text = request.form.get('minutes_text', '')
        project_id = request.form.get('project_id', type=int)

        orchestrator = get_orchestrator()
        minutes_agent = orchestrator.get_agent('minutes_reader')

        if minutes_agent:
            extractions = minutes_agent.parse_text(text, project_id)

    return render_template('pmo_agents/minutes_parser.html',
        projects=projects,
        extractions=extractions,
        page_title='Leitor de Atas'
    )


# ============================================================================
# API ENDPOINTS
# ============================================================================

@pmo_agents_bp.route('/api/briefing')
@login_required
@tenant_required
def api_briefing():
    """API: Get daily briefing as JSON."""
    orchestrator = get_orchestrator()
    briefing = orchestrator.generate_daily_briefing(current_user.full_name)
    return jsonify(briefing.to_dict())


@pmo_agents_bp.route('/api/agent/<agent_name>')
@login_required
@tenant_required
def api_run_agent(agent_name):
    """API: Run a specific agent."""
    project_id = request.args.get('project_id', type=int)

    orchestrator = get_orchestrator()
    result = orchestrator.run_agent(agent_name, project_id)

    return jsonify(result.to_dict())


@pmo_agents_bp.route('/api/agents')
@login_required
@tenant_required
def api_list_agents():
    """API: List all available agents."""
    orchestrator = get_orchestrator()
    agents_info = orchestrator.get_agent_info()
    return jsonify({'agents': agents_info})


@pmo_agents_bp.route('/api/execute-action', methods=['POST'])
@login_required
@tenant_required
def api_execute_action():
    """API: Execute a suggested action."""
    from agents.base import ActionType, Severity, ActionSuggestion

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    action = ActionSuggestion(
        action_type=ActionType(data.get('action_type')),
        title=data.get('title', ''),
        description=data.get('description', ''),
        priority=Severity(data.get('priority', 'medium')),
        project_id=data.get('project_id'),
        data=data.get('data', {})
    )

    orchestrator = get_orchestrator()
    result = orchestrator.execute_action(action)

    return jsonify(result)


@pmo_agents_bp.route('/api/project/<int:project_id>/advice')
@login_required
@tenant_required
def api_project_advice(project_id):
    """API: Get AI advice for a specific project."""
    orchestrator = get_orchestrator()
    advisor = orchestrator.get_agent('advisor_agent')

    if advisor:
        advice = advisor.get_project_recommendation(project_id)
        return jsonify(advice)

    return jsonify({'error': 'Advisor agent not available'}), 500


@pmo_agents_bp.route('/api/parse-minutes', methods=['POST'])
@login_required
@tenant_required
def api_parse_minutes():
    """API: Parse meeting minutes text."""
    data = request.get_json()
    if not data or 'text' not in data:
        return jsonify({'error': 'No text provided'}), 400

    orchestrator = get_orchestrator()
    minutes_agent = orchestrator.get_agent('minutes_reader')

    if minutes_agent:
        extractions = minutes_agent.parse_text(
            data['text'],
            data.get('project_id')
        )
        return jsonify(extractions)

    return jsonify({'error': 'Minutes reader not available'}), 500


@pmo_agents_bp.route('/api/weekly-status')
@login_required
@tenant_required
def api_weekly_status():
    """API: Generate weekly status report."""
    project_id = request.args.get('project_id', type=int)

    orchestrator = get_orchestrator()
    comm_agent = orchestrator.get_agent('communication_agent')

    if comm_agent:
        report = comm_agent.generate_weekly_status(project_id)
        return jsonify({'report': report})

    return jsonify({'error': 'Communication agent not available'}), 500


@pmo_agents_bp.route('/api/financial-scenarios/<int:project_id>')
@login_required
@tenant_required
def api_financial_scenarios(project_id):
    """API: Generate financial scenarios for a project."""
    orchestrator = get_orchestrator()
    fin_agent = orchestrator.get_agent('financial_agent')

    if fin_agent:
        scenarios = fin_agent.generate_financial_scenarios(project_id)
        return jsonify({'scenarios': scenarios})

    return jsonify({'error': 'Financial agent not available'}), 500


@pmo_agents_bp.route('/api/replan-schedule/<int:project_id>')
@login_required
@tenant_required
def api_replan_schedule(project_id):
    """API: Get schedule replan suggestions."""
    orchestrator = get_orchestrator()
    sched_agent = orchestrator.get_agent('schedule_agent')

    if sched_agent:
        suggestions = sched_agent.suggest_replan(project_id)
        return jsonify(suggestions)

    return jsonify({'error': 'Schedule agent not available'}), 500
