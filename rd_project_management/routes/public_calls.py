from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required
from models import db, PublicCall
from services.finep_scraper import scrape_finep_calls
from services.bndes_scraper import scrape_bndes_calls
import logging

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

    return render_template('public_calls/list.html',
                           calls=calls,
                           total_finep=total_finep,
                           total_bndes=total_bndes,
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


@public_calls_bp.route('/public-calls/<int:call_id>')
@login_required
def view_call(call_id):
    call = PublicCall.query.get_or_404(call_id)
    return render_template('public_calls/view.html', call=call)


@public_calls_bp.route('/public-calls/<int:call_id>/delete', methods=['POST'])
@login_required
def delete_call(call_id):
    call = PublicCall.query.get_or_404(call_id)
    db.session.delete(call)
    db.session.commit()
    flash('Chamada removida com sucesso!', 'success')
    return redirect(url_for('public_calls.list_calls'))


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
