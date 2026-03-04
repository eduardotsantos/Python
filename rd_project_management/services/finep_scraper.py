import requests
from bs4 import BeautifulSoup
import logging
import re

logger = logging.getLogger(__name__)

# Multiple URLs to try for FINEP
FINEP_URLS = [
    "http://www.finep.gov.br/chamadas-publicas?situacao=aberta",
    "http://www.finep.gov.br/chamadas-publicas",
    "http://www.finep.gov.br/apoio-e-financiamento-externa/programas-e-linhas/chamadas-publicas",
]
FINEP_BASE_URL = "http://www.finep.gov.br"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
    'Cache-Control': 'max-age=0',
}


def scrape_finep_calls():
    """
    Scrape public calls from FINEP website.
    Returns a list of dicts with call information.
    """
    all_calls = []
    seen_titles = set()

    for url in FINEP_URLS:
        try:
            logger.info(f"Tentando buscar FINEP de: {url}")
            response = requests.get(url, headers=HEADERS, timeout=30, allow_redirects=True)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Try multiple parsing strategies
            calls = []

            # Strategy 1: Look for table rows
            calls.extend(_parse_table_structure(soup))

            # Strategy 2: Look for div items (Joomla-style)
            if not calls:
                calls.extend(_parse_joomla_items(soup))

            # Strategy 3: Look for any links that seem like calls
            if not calls:
                calls.extend(_parse_links_strategy(soup))

            # Add unique calls
            for call in calls:
                if call.get('title') and call['title'] not in seen_titles:
                    seen_titles.add(call['title'])
                    all_calls.append(call)

            if all_calls:
                logger.info(f"FINEP: Encontradas {len(all_calls)} chamadas de {url}")
                # Continue trying other URLs to get more calls

        except requests.RequestException as e:
            logger.warning(f"Erro ao buscar FINEP ({url}): {e}")
        except Exception as e:
            logger.error(f"Erro ao processar FINEP ({url}): {e}")

    logger.info(f"FINEP: Total de {len(all_calls)} chamadas públicas encontradas")
    return all_calls


def _parse_table_structure(soup):
    """Parse table-based structure."""
    calls = []

    # Look for tables with call listings
    tables = soup.find_all('table')
    for table in tables:
        rows = table.find_all('tr')
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 1:
                link = row.find('a', href=True)
                if link:
                    text = link.get_text(strip=True)
                    href = link['href']
                    if text and len(text) > 10 and _is_valid_call_text(text):
                        call = _create_call_dict(text, href)

                        # Try to get date from other cells
                        for cell in cells:
                            cell_text = cell.get_text(strip=True)
                            if _looks_like_date(cell_text):
                                call['publication_date'] = cell_text
                                break

                        calls.append(call)

    return calls


def _parse_joomla_items(soup):
    """Parse Joomla-style content items."""
    calls = []
    seen_titles = set()

    # Various Joomla selectors
    selectors = [
        'div.items-row',
        'div.item-page',
        'div.blog-items div.item',
        'div.com-content-category-blog__items > div',
        'ul.category li',
        'div.category-list li',
        'div[class*="chamada"]',
        'article',
        'div.item',
    ]

    for selector in selectors:
        items = soup.select(selector)
        for item in items:
            # Try to find all links in the item
            links = item.find_all('a', href=True)
            for link in links:
                text = link.get_text(strip=True)
                href = link['href']
                if text and len(text) > 15 and _is_valid_call_text(text) and text not in seen_titles:
                    seen_titles.add(text)
                    call = _create_call_dict(text, href)

                    # Try to find date
                    date_el = item.find(['time', 'span'], class_=lambda x: x and 'date' in x.lower() if x else False)
                    if date_el:
                        call['publication_date'] = date_el.get_text(strip=True)

                    # Try to find description
                    desc_el = item.find(['p', 'div'], class_=lambda x: x and ('intro' in x.lower() or 'desc' in x.lower()) if x else False)
                    if desc_el:
                        call['description'] = desc_el.get_text(strip=True)[:500]

                    calls.append(call)

        # Continue checking other selectors to find more calls

    return calls


def _parse_links_strategy(soup):
    """Parse by finding all valid links in the content area."""
    calls = []
    seen = set()

    # Try to find main content area
    content_areas = soup.select('div#content, main, div.item-page, div#component, div[role="main"], body')

    for content in content_areas:
        links = content.find_all('a', href=True)
        for link in links:
            text = link.get_text(strip=True)
            href = link['href']

            # Skip navigation, footer links, etc.
            if not text or len(text) < 15:
                continue
            if text in seen:
                continue
            if not _is_valid_call_text(text):
                continue

            # Skip certain patterns
            parent = link.parent
            if parent:
                parent_class = parent.get('class', [])
                if any(c in str(parent_class).lower() for c in ['nav', 'menu', 'footer', 'breadcrumb']):
                    continue

            seen.add(text)
            calls.append(_create_call_dict(text, href))

        # Continue searching all content areas

    return calls


def _create_call_dict(title, href):
    """Create a standardized call dictionary."""
    url = href if href.startswith('http') else FINEP_BASE_URL + href

    return {
        'source': 'FINEP',
        'title': title,
        'theme': _extract_theme(title),
        'description': title,
        'publication_date': '',
        'funding_source': 'FINEP / FNDCT',
        'target_audience': 'Empresas, ICTs e Pesquisadores',
        'url': url,
    }


def _is_valid_call_text(text):
    """Check if text looks like a public call title."""
    text_lower = text.lower()

    # Must contain at least one of these keywords
    keywords = [
        'chamada', 'edital', 'seleção', 'selecao', 'programa',
        'subvenção', 'subvencao', 'encomenda', 'fndct',
        'inovação', 'inovacao', 'pesquisa', 'desenvolvimento',
        'tecnologia', 'ct-', 'finep', 'fundo', 'apoio',
        'mcti', 'mctic', 'cnpq', 'recurso', 'financiamento',
        'projeto', 'pública', 'publica', 'aberta', 'vigente',
        'carta convite', 'convite', 'credenciamento', 'startups',
        'empresas', 'ict', 'universidade', 'instituição',
        'infraestrutura', 'capacitação', 'bolsa', 'fomento',
    ]

    # Negative keywords - skip if contains
    skip_keywords = [
        'resultado', 'retificação', 'retificacao', 'errata',
        'prorrogação', 'prorrogacao', 'suspensão', 'suspensao',
        'voltar', 'menu', 'leia mais', 'saiba mais',
        'home', 'início', 'inicio', 'contato', 'fale conosco',
        'login', 'cadastro', 'acessar', 'entrar', 'sair',
        'twitter', 'facebook', 'instagram', 'linkedin',
    ]

    has_keyword = any(kw in text_lower for kw in keywords)
    has_skip = any(kw in text_lower for kw in skip_keywords)

    return has_keyword and not has_skip


def _looks_like_date(text):
    """Check if text looks like a date."""
    # Brazilian date patterns
    date_patterns = [
        r'\d{1,2}/\d{1,2}/\d{2,4}',  # DD/MM/YYYY or DD/MM/YY
        r'\d{1,2}\s+de\s+\w+\s+de\s+\d{4}',  # DD de Mês de YYYY
    ]

    for pattern in date_patterns:
        if re.search(pattern, text):
            return True
    return False


def _extract_theme(title):
    """Extract theme from the title."""
    themes = {
        'saúde': 'Saúde',
        'saude': 'Saúde',
        'energia': 'Energia',
        'agro': 'Agropecuária',
        'tic': 'Tecnologia da Informação',
        'digital': 'Transformação Digital',
        'sustent': 'Sustentabilidade',
        'defesa': 'Defesa',
        'aeroesp': 'Aeroespacial',
        'biotech': 'Biotecnologia',
        'biotec': 'Biotecnologia',
        'nano': 'Nanotecnologia',
        'inovação': 'Inovação',
        'inovacao': 'Inovação',
        'subvenção': 'Subvenção Econômica',
        'subvencao': 'Subvenção Econômica',
        'ct-': 'Fundo Setorial',
        'fndct': 'FNDCT',
        'infraestrutura': 'Infraestrutura',
        'petro': 'Petróleo e Gás',
        'mineral': 'Mineração',
        'agua': 'Recursos Hídricos',
        'água': 'Recursos Hídricos',
        'transporte': 'Transportes',
        'espacial': 'Espacial',
        'nuclear': 'Nuclear',
    }

    title_lower = title.lower()
    for key, value in themes.items():
        if key in title_lower:
            return value

    return 'Ciência, Tecnologia e Inovação'
