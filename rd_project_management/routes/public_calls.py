from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required
from models import db, PublicCall, Project, ProjectCall
from services.finep_scraper import scrape_finep_calls
from services.bndes_scraper import scrape_bndes_calls
from datetime import datetime, date
import logging
import re

logger = logging.getLogger(__name__)

public_calls_bp = Blueprint('public_calls', __name__)


@public_calls_bp.route('/public-calls')
@login_required
def list_calls():
    source_filter = request.args.get('source', '')
    search = request.args.get('search', '')

    query = PublicCall.query
    if source_filter:
        query = query.filter_by(source=source_filter)
    if search:
        query = query.filter(
            db.or_(
                PublicCall.title.ilike(f'%{search}%'),
                PublicCall.description.ilike(f'%{search}%'),
                PublicCall.theme.ilike(f'%{search}%')
            )
        )

    calls = query.order_by(PublicCall.updated_at.desc()).all()
    total_finep = PublicCall.query.filter_by(source='FINEP').count()
    total_bndes = PublicCall.query.filter_by(source='BNDES').count()

    total_other = PublicCall.query.filter(~PublicCall.source.in_(['FINEP', 'BNDES'])).count()

    return render_template('public_calls/list.html',
                           calls=calls,
                           total_finep=total_finep,
                           total_bndes=total_bndes,
                           total_other=total_other,
                           source_filter=source_filter,
                           search=search)


@public_calls_bp.route('/public-calls/refresh', methods=['POST'])
@login_required
def refresh_calls():
    """Manually trigger a refresh of public calls from FINEP and BNDES."""
    results = {'finep': 0, 'bndes': 0, 'errors': []}

    # Scrape FINEP
    try:
        finep_calls = scrape_finep_calls()
        for call_data in finep_calls:
            _upsert_call(call_data)
        results['finep'] = len(finep_calls)
    except Exception as e:
        logger.error(f"Error refreshing FINEP: {e}")
        results['errors'].append(f'FINEP: {str(e)}')

    # Scrape BNDES
    try:
        bndes_calls = scrape_bndes_calls()
        for call_data in bndes_calls:
            _upsert_call(call_data)
        results['bndes'] = len(bndes_calls)
    except Exception as e:
        logger.error(f"Error refreshing BNDES: {e}")
        results['errors'].append(f'BNDES: {str(e)}')

    db.session.commit()

    if results['errors']:
        flash(f'Atualização parcial. FINEP: {results["finep"]} chamadas. '
              f'BNDES: {results["bndes"]} chamadas. '
              f'Erros: {"; ".join(results["errors"])}', 'warning')
    else:
        flash(f'Atualização concluída! FINEP: {results["finep"]} chamadas. '
              f'BNDES: {results["bndes"]} chamadas.', 'success')

    return redirect(url_for('public_calls.list_calls'))


@public_calls_bp.route('/public-calls/refresh-ajax', methods=['POST'])
@login_required
def refresh_calls_ajax():
    """AJAX endpoint for refreshing calls."""
    results = {'finep': 0, 'bndes': 0, 'errors': []}

    try:
        finep_calls = scrape_finep_calls()
        for call_data in finep_calls:
            _upsert_call(call_data)
        results['finep'] = len(finep_calls)
    except Exception as e:
        results['errors'].append(f'FINEP: {str(e)}')

    try:
        bndes_calls = scrape_bndes_calls()
        for call_data in bndes_calls:
            _upsert_call(call_data)
        results['bndes'] = len(bndes_calls)
    except Exception as e:
        results['errors'].append(f'BNDES: {str(e)}')

    db.session.commit()
    return jsonify(results)


@public_calls_bp.route('/public-calls/new', methods=['GET', 'POST'])
@login_required
def create_call():
    """Manually create a public call."""
    if request.method == 'POST':
        call = PublicCall(
            source=request.form.get('source', '').strip() or 'Outro',
            title=request.form.get('title', '').strip(),
            theme=request.form.get('theme', '').strip(),
            description=request.form.get('description', '').strip(),
            publication_date=request.form.get('publication_date', '').strip(),
            deadline=request.form.get('deadline', '').strip(),
            funding_source=request.form.get('funding_source', '').strip(),
            target_audience=request.form.get('target_audience', '').strip(),
            url=request.form.get('url', '').strip(),
            status=request.form.get('status', 'Aberta'),
        )
        db.session.add(call)
        db.session.commit()
        flash('Chamada pública cadastrada com sucesso!', 'success')
        return redirect(url_for('public_calls.list_calls'))

    return render_template('public_calls/form.html', call=None)


@public_calls_bp.route('/public-calls/<int:call_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_call(call_id):
    """Edit a public call."""
    call = PublicCall.query.get_or_404(call_id)

    if request.method == 'POST':
        call.source = request.form.get('source', '').strip() or call.source
        call.title = request.form.get('title', '').strip()
        call.theme = request.form.get('theme', '').strip()
        call.description = request.form.get('description', '').strip()
        call.publication_date = request.form.get('publication_date', '').strip()
        call.deadline = request.form.get('deadline', '').strip()
        call.funding_source = request.form.get('funding_source', '').strip()
        call.target_audience = request.form.get('target_audience', '').strip()
        call.url = request.form.get('url', '').strip()
        call.status = request.form.get('status', call.status)

        db.session.commit()
        flash('Chamada atualizada com sucesso!', 'success')
        return redirect(url_for('public_calls.view_call', call_id=call_id))

    return render_template('public_calls/form.html', call=call)


@public_calls_bp.route('/public-calls/<int:call_id>')
@login_required
def view_call(call_id):
    call = PublicCall.query.get_or_404(call_id)
    projects = Project.query.order_by(Project.title).all()
    return render_template('public_calls/view.html', call=call, projects=projects)


@public_calls_bp.route('/public-calls/<int:call_id>/delete', methods=['POST'])
@login_required
def delete_call(call_id):
    call = PublicCall.query.get_or_404(call_id)
    db.session.delete(call)
    db.session.commit()
    flash('Chamada removida com sucesso!', 'success')
    return redirect(url_for('public_calls.list_calls'))


@public_calls_bp.route('/public-calls/<int:call_id>/link', methods=['POST'])
@login_required
def link_to_project(call_id):
    """Link a public call to a project."""
    call = PublicCall.query.get_or_404(call_id)
    project_id = request.form.get('project_id')
    linked_at = request.form.get('linked_at', '')
    notes = request.form.get('link_notes', '').strip()
    status = request.form.get('link_status', 'Vinculado')

    if not project_id:
        flash('Selecione um projeto para vincular.', 'warning')
        return redirect(url_for('public_calls.view_call', call_id=call_id))

    # Check if link already exists
    existing = ProjectCall.query.filter_by(
        project_id=int(project_id),
        public_call_id=call_id
    ).first()

    if existing:
        flash('Este projeto já está vinculado a esta chamada.', 'warning')
        return redirect(url_for('public_calls.view_call', call_id=call_id))

    link = ProjectCall(
        project_id=int(project_id),
        public_call_id=call_id,
        linked_at=datetime.strptime(linked_at, '%Y-%m-%d').date() if linked_at else date.today(),
        notes=notes,
        status=status
    )
    db.session.add(link)
    db.session.commit()
    flash('Projeto vinculado com sucesso!', 'success')
    return redirect(url_for('public_calls.view_call', call_id=call_id))


@public_calls_bp.route('/public-calls/<int:call_id>/unlink/<int:link_id>', methods=['POST'])
@login_required
def unlink_project(call_id, link_id):
    """Remove a project link."""
    link = ProjectCall.query.get_or_404(link_id)
    db.session.delete(link)
    db.session.commit()
    flash('Vínculo removido com sucesso!', 'success')
    return redirect(url_for('public_calls.view_call', call_id=call_id))


@public_calls_bp.route('/public-calls/suggest-links', methods=['POST'])
@login_required
def suggest_links():
    """Automatically suggest links between projects and public calls based on keywords."""
    count = 0
    projects = Project.query.all()
    calls = PublicCall.query.all()

    for call in calls:
        call_keywords = _extract_keywords(call.title + ' ' + (call.description or '') + ' ' + (call.theme or ''))

        for project in projects:
            # Check if link already exists
            existing = ProjectCall.query.filter_by(
                project_id=project.id,
                public_call_id=call.id
            ).first()

            if existing:
                continue

            project_keywords = _extract_keywords(
                project.title + ' ' + (project.description or '') + ' ' +
                (project.category or '') + ' ' + (project.funding_source or '')
            )

            # Calculate match score
            common_keywords = call_keywords & project_keywords
            if len(common_keywords) >= 2:  # At least 2 matching keywords
                link = ProjectCall(
                    project_id=project.id,
                    public_call_id=call.id,
                    linked_at=date.today(),
                    notes='Sugerido automaticamente',
                    status='Sugerido'
                )
                db.session.add(link)
                count += 1

    db.session.commit()

    return jsonify({
        'success': count > 0,
        'count': count,
        'message': f'{count} vínculos sugeridos' if count > 0 else 'Nenhuma correspondência encontrada'
    })


def _extract_keywords(text):
    """Extract relevant keywords from text."""
    if not text:
        return set()

    text = text.lower()
    # Remove accents and special characters
    text = re.sub(r'[^\w\s]', ' ', text)

    # Split into words
    words = text.split()

    # Filter short words and common stop words
    stop_words = {
        'de', 'da', 'do', 'das', 'dos', 'em', 'para', 'com', 'por', 'uma', 'um',
        'que', 'se', 'na', 'no', 'nas', 'nos', 'ao', 'aos', 'ou', 'e', 'a', 'o',
        'os', 'as', 'como', 'mais', 'menos', 'entre', 'sobre', 'este', 'esta',
        'esse', 'essa', 'isto', 'isso', 'aquele', 'aquela', 'seu', 'sua', 'seus',
        'suas', 'meu', 'minha', 'nosso', 'nossa', 'ter', 'ser', 'estar', 'haver',
        'quando', 'onde', 'qual', 'quais', 'todo', 'toda', 'todos', 'todas'
    }

    keywords = set()
    for word in words:
        if len(word) >= 4 and word not in stop_words:
            keywords.add(word)

    return keywords


def _upsert_call(call_data):
    """Insert or update a public call."""
    existing = PublicCall.query.filter_by(
        source=call_data['source'],
        title=call_data['title']
    ).first()

    if existing:
        # Update existing
        existing.theme = call_data.get('theme', existing.theme)
        existing.description = call_data.get('description', existing.description)
        existing.publication_date = call_data.get('publication_date', existing.publication_date)
        existing.funding_source = call_data.get('funding_source', existing.funding_source)
        existing.target_audience = call_data.get('target_audience', existing.target_audience)
        if call_data.get('url'):
            existing.url = call_data['url']
    else:
        # Create new
        new_call = PublicCall(
            source=call_data['source'],
            title=call_data['title'],
            theme=call_data.get('theme', ''),
            description=call_data.get('description', ''),
            publication_date=call_data.get('publication_date', ''),
            funding_source=call_data.get('funding_source', ''),
            target_audience=call_data.get('target_audience', ''),
            url=call_data.get('url', ''),
        )
        db.session.add(new_call)
