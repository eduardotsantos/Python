import requests
from bs4 import BeautifulSoup
import logging
import json

logger = logging.getLogger(__name__)

BNDES_EDITAIS_URL = "https://www.bndes.gov.br/wps/portal/site/home/financiamento/editais"
BNDES_CHAMADAS_URL = "https://www.bndes.gov.br/wps/portal/site/home/financiamento/chamadas-publicas"
BNDES_BASE_URL = "https://www.bndes.gov.br"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
}


def scrape_bndes_calls():
    """
    Scrape public calls and editais from BNDES website.
    Returns a list of dicts with call information.
    """
    calls = []

    # Try both URLs
    for url in [BNDES_EDITAIS_URL, BNDES_CHAMADAS_URL]:
        try:
            response = requests.get(url, headers=HEADERS, timeout=30, verify=True)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            page_calls = _parse_bndes_page(soup, url)
            calls.extend(page_calls)

        except requests.RequestException as e:
            logger.error(f"Error fetching BNDES ({url}): {e}")
        except Exception as e:
            logger.error(f"Error parsing BNDES ({url}): {e}")

    # Deduplicate by title
    seen = set()
    unique_calls = []
    for call in calls:
        if call['title'] not in seen:
            seen.add(call['title'])
            unique_calls.append(call)

    logger.info(f"BNDES: Found {len(unique_calls)} public calls")
    return unique_calls


def _parse_bndes_page(soup, page_url):
    """Parse BNDES page for public calls."""
    calls = []

    # Try multiple content selectors
    content_selectors = [
        'div.editais-lista div.item',
        'div.lista-editais div.edital',
        'ul.lista-resultados li',
        'div.content-area article',
        'div.wpthemeControlBody div.item',
        'table tbody tr',
        'div.component-content div.item',
        'div[class*="edital"]',
        'div[class*="chamada"]',
    ]

    items = []
    for selector in content_selectors:
        items = soup.select(selector)
        if items:
            break

    if items:
        for item in items:
            call = _parse_bndes_item(item)
            if call and call.get('title'):
                calls.append(call)

    # Fallback: extract links from content area
    if not calls:
        content = soup.select_one(
            'div.wpthemeControlBody, div#content, main, '
            'div.component-content, div[role="main"]'
        )
        if content:
            calls = _extract_bndes_links(content)

    # Final fallback: look for any relevant links
    if not calls:
        calls = _extract_bndes_links(soup)

    return calls


def _parse_bndes_item(item):
    """Parse a single BNDES item element."""
    call = {
        'source': 'BNDES',
        'title': '',
        'theme': '',
        'description': '',
        'publication_date': '',
        'funding_source': 'BNDES',
        'target_audience': '',
        'url': '',
    }

    # Title
    title_el = item.select_one('h2 a, h3 a, h4 a, a, .titulo, .title')
    if title_el:
        call['title'] = title_el.get_text(strip=True)
        href = title_el.get('href', '')
        if href:
            call['url'] = href if href.startswith('http') else BNDES_BASE_URL + href

    # Description
    desc_el = item.select_one('p, .descricao, .description, .resumo')
    if desc_el:
        call['description'] = desc_el.get_text(strip=True)[:500]

    # Date
    date_el = item.select_one('.data, .date, time, span[class*="date"]')
    if date_el:
        call['publication_date'] = date_el.get_text(strip=True)

    # Status/Target
    status_el = item.select_one('.status, .situacao')
    if status_el:
        call['target_audience'] = status_el.get_text(strip=True)

    if not call['target_audience']:
        call['target_audience'] = 'Empresas e Instituições'

    call['theme'] = _extract_bndes_theme(call['title'] + ' ' + call['description'])

    return call


def _extract_bndes_links(container):
    """Extract relevant links from BNDES page."""
    calls = []
    seen_titles = set()

    links = container.find_all('a', href=True)
    for link in links:
        text = link.get_text(strip=True)
        href = link['href']

        if (text and len(text) > 15 and text not in seen_titles
                and _is_valid_bndes_link(text, href)):
            seen_titles.add(text)
            url = href if href.startswith('http') else BNDES_BASE_URL + href
            calls.append({
                'source': 'BNDES',
                'title': text,
                'theme': _extract_bndes_theme(text),
                'description': text,
                'publication_date': '',
                'funding_source': 'BNDES',
                'target_audience': 'Empresas e Instituições',
                'url': url,
            })

    return calls


def _is_valid_bndes_link(text, href):
    """Check if a link seems to be a public call."""
    text_lower = text.lower()
    href_lower = href.lower()

    keywords = ['edital', 'chamada', 'seleção', 'programa', 'credenciamento',
                'licitação', 'concorrência', 'pregão', 'convocação',
                'inovação', 'fundo', 'financiamento']

    # Check text
    if any(kw in text_lower for kw in keywords):
        return True

    # Check URL path
    if any(kw in href_lower for kw in ['edital', 'chamada', 'selecao', 'programa']):
        return True

    return False


def _extract_bndes_theme(text):
    """Extract theme from BNDES call text."""
    themes = {
        'inovação': 'Inovação',
        'infraestrutura': 'Infraestrutura',
        'sustent': 'Sustentabilidade',
        'social': 'Desenvolvimento Social',
        'agro': 'Agropecuária',
        'indústria': 'Indústria',
        'saúde': 'Saúde',
        'educação': 'Educação',
        'energia': 'Energia',
        'digital': 'Transformação Digital',
        'micro': 'Micro e Pequenas Empresas',
        'exporta': 'Comércio Exterior',
        'clima': 'Mudança Climática',
        'amazon': 'Amazônia',
        'fundo': 'Fundo de Desenvolvimento',
    }
    text_lower = text.lower()
    for key, value in themes.items():
        if key in text_lower:
            return value
    return 'Desenvolvimento Econômico e Social'
