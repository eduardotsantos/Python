import requests
from bs4 import BeautifulSoup
import logging
import re
import urllib3

# Disable SSL warnings for sites with certificate issues
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

FAPESC_URL = "https://fapesc.sc.gov.br/chamadas-abertas/"
FAPESC_BASE_URL = "https://fapesc.sc.gov.br"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Cache-Control': 'max-age=0',
}


def scrape_fapesc_calls():
    """
    Scrape public calls from FAPESC website.
    Returns a list of dicts with call information.
    """
    calls = []
    seen_titles = set()

    try:
        logger.info(f"Buscando chamadas FAPESC de: {FAPESC_URL}")

        # Use a session for better cookie handling
        session = requests.Session()
        session.headers.update(HEADERS)

        # First request to get cookies
        session.get(FAPESC_BASE_URL, timeout=10, verify=False)

        # Now fetch the actual page
        response = session.get(FAPESC_URL, timeout=30, verify=False)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Strategy 1: Look for article/post elements (WordPress style)
        calls.extend(_parse_wordpress_posts(soup, seen_titles))

        # Strategy 2: Look for list items with links
        if not calls:
            calls.extend(_parse_list_items(soup, seen_titles))

        # Strategy 3: Look for any content links
        if not calls:
            calls.extend(_parse_content_links(soup, seen_titles))

        logger.info(f"FAPESC: Encontradas {len(calls)} chamadas públicas")

    except requests.RequestException as e:
        logger.error(f"Erro ao buscar FAPESC: {e}")
    except Exception as e:
        logger.error(f"Erro ao processar FAPESC: {e}")

    return calls


def _parse_wordpress_posts(soup, seen_titles):
    """Parse WordPress-style post listings."""
    calls = []

    # Common WordPress selectors
    selectors = [
        'article',
        'div.post',
        'div.entry',
        'div.chamada',
        'div.edital',
        'li.post',
        'div.wp-block-post',
        'div.elementor-post',
        'div.card',
        'div.item',
    ]

    for selector in selectors:
        items = soup.select(selector)
        for item in items:
            call = _extract_call_from_element(item, seen_titles)
            if call:
                calls.append(call)

    return calls


def _parse_list_items(soup, seen_titles):
    """Parse list-based structure."""
    calls = []

    # Find lists that might contain calls
    lists = soup.find_all(['ul', 'ol'], class_=lambda x: x and any(
        kw in str(x).lower() for kw in ['chamada', 'edital', 'post', 'list', 'items']
    ) if x else False)

    # Also try lists inside main content
    main_content = soup.find(['main', 'article', 'div'], class_=lambda x: x and any(
        kw in str(x).lower() for kw in ['content', 'main', 'container']
    ) if x else False)

    if main_content:
        lists.extend(main_content.find_all(['ul', 'ol']))

    for lst in lists:
        items = lst.find_all('li')
        for item in items:
            call = _extract_call_from_element(item, seen_titles)
            if call:
                calls.append(call)

    return calls


def _parse_content_links(soup, seen_titles):
    """Parse by finding all valid links in content area."""
    calls = []

    # Find main content area
    content_areas = soup.select('main, article, div.content, div.container, div#content, div.page-content')

    if not content_areas:
        content_areas = [soup.body] if soup.body else []

    for content in content_areas:
        links = content.find_all('a', href=True)
        for link in links:
            text = link.get_text(strip=True)
            href = link['href']

            if not text or len(text) < 10:
                continue
            if text in seen_titles:
                continue
            if not _is_valid_call_text(text):
                continue

            # Skip navigation links
            parent = link.parent
            if parent:
                parent_class = str(parent.get('class', []))
                if any(skip in parent_class.lower() for skip in ['nav', 'menu', 'footer', 'header', 'sidebar']):
                    continue

            seen_titles.add(text)
            calls.append(_create_call_dict(text, href))

    return calls


def _extract_call_from_element(element, seen_titles):
    """Extract call information from an HTML element."""
    # Find the main link
    link = element.find('a', href=True)
    if not link:
        return None

    title = link.get_text(strip=True)
    href = link['href']

    # Skip if invalid
    if not title or len(title) < 10:
        return None
    if title in seen_titles:
        return None
    if not _is_valid_call_text(title):
        return None

    seen_titles.add(title)
    call = _create_call_dict(title, href)

    # Try to extract additional info
    # Date
    date_el = element.find(['time', 'span', 'div'], class_=lambda x: x and any(
        kw in str(x).lower() for kw in ['date', 'data', 'time', 'posted']
    ) if x else False)
    if date_el:
        call['publication_date'] = date_el.get_text(strip=True)

    # Also check for date in text
    if not call['publication_date']:
        text = element.get_text()
        date_match = re.search(r'\d{1,2}/\d{1,2}/\d{2,4}', text)
        if date_match:
            call['publication_date'] = date_match.group()

    # Description/excerpt
    desc_el = element.find(['p', 'div', 'span'], class_=lambda x: x and any(
        kw in str(x).lower() for kw in ['excerpt', 'summary', 'desc', 'resumo', 'intro']
    ) if x else False)
    if desc_el:
        call['description'] = desc_el.get_text(strip=True)[:500]

    # Deadline
    deadline_el = element.find(string=re.compile(r'prazo|encerra|deadline|até|validade', re.I))
    if deadline_el:
        parent_text = deadline_el.parent.get_text(strip=True) if deadline_el.parent else str(deadline_el)
        date_match = re.search(r'\d{1,2}/\d{1,2}/\d{2,4}', parent_text)
        if date_match:
            call['deadline'] = date_match.group()

    return call


def _create_call_dict(title, href):
    """Create a standardized call dictionary."""
    url = href if href.startswith('http') else FAPESC_BASE_URL + href

    return {
        'source': 'FAPESC',
        'title': title,
        'theme': _extract_theme(title),
        'description': title,
        'publication_date': '',
        'deadline': '',
        'funding_source': 'FAPESC - Fundação de Amparo à Pesquisa e Inovação do Estado de Santa Catarina',
        'target_audience': 'Pesquisadores, ICTs e Empresas de SC',
        'url': url,
    }


def _is_valid_call_text(text):
    """Check if text looks like a public call title."""
    text_lower = text.lower()

    # Must contain at least one keyword
    keywords = [
        'chamada', 'edital', 'seleção', 'selecao', 'programa',
        'fomento', 'apoio', 'bolsa', 'pesquisa', 'inovação', 'inovacao',
        'tecnologia', 'desenvolvimento', 'projeto', 'subvenção', 'subvencao',
        'fapesc', 'ct&i', 'cti', 'ict', 'universidade', 'empresa',
        'startups', 'startup', 'incubadora', 'parque tecnológico',
        'mestrado', 'doutorado', 'pós-graduação', 'graduação',
        'iniciação científica', 'extensão', 'infraestrutura',
        'equipamento', 'laboratório', 'publicação', 'evento',
        'intercâmbio', 'mobilidade', 'capacitação', 'formação',
    ]

    # Skip keywords
    skip_keywords = [
        'resultado', 'retificação', 'retificacao', 'errata',
        'prorrogação', 'prorrogacao', 'suspensão', 'suspensao',
        'cancelamento', 'cancelada', 'encerrada', 'encerrado',
        'voltar', 'menu', 'leia mais', 'saiba mais', 'ver mais',
        'home', 'início', 'inicio', 'contato', 'fale conosco',
        'login', 'cadastro', 'acessar', 'entrar', 'sair',
        'twitter', 'facebook', 'instagram', 'linkedin', 'youtube',
        'política de privacidade', 'termos de uso',
    ]

    has_keyword = any(kw in text_lower for kw in keywords)
    has_skip = any(kw in text_lower for kw in skip_keywords)

    return has_keyword and not has_skip


def _extract_theme(title):
    """Extract theme from the title."""
    themes = {
        'saúde': 'Saúde',
        'saude': 'Saúde',
        'agro': 'Agropecuária',
        'energia': 'Energia',
        'tic': 'Tecnologia da Informação',
        'digital': 'Transformação Digital',
        'sustent': 'Sustentabilidade',
        'meio ambiente': 'Meio Ambiente',
        'biodiversidade': 'Biodiversidade',
        'biotech': 'Biotecnologia',
        'biotec': 'Biotecnologia',
        'inovação': 'Inovação',
        'inovacao': 'Inovação',
        'startup': 'Startups',
        'empreend': 'Empreendedorismo',
        'bolsa': 'Bolsas',
        'mestrado': 'Pós-Graduação',
        'doutorado': 'Pós-Graduação',
        'iniciação científica': 'Iniciação Científica',
        'infraestrutura': 'Infraestrutura',
        'equipamento': 'Equipamentos',
        'laboratório': 'Laboratórios',
        'evento': 'Eventos Científicos',
        'publicação': 'Publicações',
        'extensão': 'Extensão',
        'social': 'Inovação Social',
        'educação': 'Educação',
        'educacao': 'Educação',
        'turismo': 'Turismo',
        'mar': 'Economia do Mar',
        'oceano': 'Economia do Mar',
        'pesca': 'Pesca e Aquicultura',
    }

    title_lower = title.lower()
    for key, value in themes.items():
        if key in title_lower:
            return value

    return 'Ciência, Tecnologia e Inovação'
