import requests
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

FINEP_CHAMADAS_URL = "http://www.finep.gov.br/chamadas-publicas"
FINEP_BASE_URL = "http://www.finep.gov.br"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
}


def scrape_finep_calls():
    """
    Scrape public calls from FINEP website.
    Returns a list of dicts with call information.
    """
    calls = []

    try:
        response = requests.get(FINEP_CHAMADAS_URL, headers=HEADERS, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'lxml')

        # FINEP uses various page structures - try multiple selectors
        # Try main content area with list items or articles
        content_selectors = [
            'div.items-row',
            'div.item-page',
            'table.category tbody tr',
            'div#content article',
            'div.blog-items div.item',
            'ul.category li',
            'div.com-content-category-blog__items div',
        ]

        items = []
        for selector in content_selectors:
            items = soup.select(selector)
            if items:
                break

        if items:
            for item in items:
                call = _parse_finep_item(item)
                if call and call.get('title'):
                    calls.append(call)

        # If no structured items found, try extracting links from content
        if not calls:
            content_area = soup.select_one('div#content, div.item-page, main, div#component')
            if content_area:
                links = content_area.find_all('a', href=True)
                for link in links:
                    text = link.get_text(strip=True)
                    href = link['href']
                    if text and len(text) > 15 and _is_valid_call_link(text):
                        url = href if href.startswith('http') else FINEP_BASE_URL + href
                        call = {
                            'source': 'FINEP',
                            'title': text,
                            'theme': _extract_theme(text),
                            'description': text,
                            'publication_date': '',
                            'funding_source': 'FINEP',
                            'target_audience': 'Empresas e ICTs',
                            'url': url,
                        }
                        calls.append(call)

        # Also try to get details from subpages
        if not calls:
            calls = _try_alternative_finep_scrape(soup)

        logger.info(f"FINEP: Found {len(calls)} public calls")

    except requests.RequestException as e:
        logger.error(f"Error fetching FINEP calls: {e}")
    except Exception as e:
        logger.error(f"Error parsing FINEP calls: {e}")

    return calls


def _parse_finep_item(item):
    """Parse a single FINEP item element."""
    call = {
        'source': 'FINEP',
        'title': '',
        'theme': '',
        'description': '',
        'publication_date': '',
        'funding_source': 'FINEP',
        'target_audience': '',
        'url': '',
    }

    # Try to find title
    title_el = item.select_one('h2 a, h3 a, h4 a, a.mod-articles-category-title, td a, a')
    if title_el:
        call['title'] = title_el.get_text(strip=True)
        href = title_el.get('href', '')
        call['url'] = href if href.startswith('http') else FINEP_BASE_URL + href

    # Try to find description
    desc_el = item.select_one('div.intro, p, div.item-content, td:nth-of-type(2)')
    if desc_el:
        call['description'] = desc_el.get_text(strip=True)[:500]

    # Try to find date
    date_el = item.select_one('time, span.date, dd.published, td.list-date')
    if date_el:
        call['publication_date'] = date_el.get_text(strip=True)

    call['theme'] = _extract_theme(call['title'])
    call['target_audience'] = 'Empresas, ICTs e Pesquisadores'

    return call


def _is_valid_call_link(text):
    """Check if a link text looks like a public call."""
    keywords = ['chamada', 'edital', 'seleção', 'programa', 'subvenção',
                'encomenda', 'fndct', 'inovação', 'pesquisa']
    text_lower = text.lower()
    return any(kw in text_lower for kw in keywords)


def _extract_theme(title):
    """Extract theme from the title."""
    themes = {
        'saúde': 'Saúde',
        'energia': 'Energia',
        'agro': 'Agropecuária',
        'tic': 'Tecnologia da Informação',
        'digital': 'Transformação Digital',
        'sustent': 'Sustentabilidade',
        'defesa': 'Defesa',
        'aeroesp': 'Aeroespacial',
        'biotech': 'Biotecnologia',
        'nano': 'Nanotecnologia',
        'inovação': 'Inovação',
        'subvenção': 'Subvenção Econômica',
    }
    title_lower = title.lower()
    for key, value in themes.items():
        if key in title_lower:
            return value
    return 'Ciência, Tecnologia e Inovação'


def _try_alternative_finep_scrape(soup):
    """Try alternative scraping approaches for FINEP."""
    calls = []

    # Try finding any content blocks with call-like information
    all_links = soup.find_all('a', href=True)
    seen_titles = set()
    for link in all_links:
        text = link.get_text(strip=True)
        href = link['href']
        if (text and len(text) > 20 and text not in seen_titles
                and _is_valid_call_link(text)):
            seen_titles.add(text)
            url = href if href.startswith('http') else FINEP_BASE_URL + href
            calls.append({
                'source': 'FINEP',
                'title': text,
                'theme': _extract_theme(text),
                'description': text,
                'publication_date': '',
                'funding_source': 'FINEP',
                'target_audience': 'Empresas e ICTs',
                'url': url,
            })

    return calls
