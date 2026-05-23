"""Scraper for FAPESC public calls - improved version with proper parsing."""

import requests
from bs4 import BeautifulSoup
import logging
import re
import urllib3
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

FAPESC_URLS = [
    "https://fapesc.sc.gov.br/chamadas-abertas/",
    "https://fapesc.sc.gov.br/category/chamadas-abertas/",
    "https://fapesc.sc.gov.br/category/chamadas-abertas/page/2/",
    "https://fapesc.sc.gov.br/chamadas-em-andamento/",
]

FAPESC_BASE_URL = "https://fapesc.sc.gov.br"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
    'Referer': 'https://fapesc.sc.gov.br/',
}

VALID_KEYWORDS = [
    'edital', 'chamada', 'programa', 'seleção', 'selecao', 'bolsa',
    'fomento', 'apoio', 'projeto', 'pesquisa', 'inovação', 'inovacao',
    'subvenção', 'subvencao', 'sinapse', 'centelha', 'tecnova',
    'inova', 'cnpq', 'fap', 'ict'
]

EXCLUDE_KEYWORDS = [
    'resultado', 'retificação', 'retificacao', 'errata', 'prorrogação',
    'prorrogacao', 'homologação', 'homologacao', 'classificação',
    'classificacao', 'recurso', 'menu', 'voltar', 'home', 'contato',
    'acesso', 'login', 'cadastro', 'notícia', 'noticia', 'ver mais',
    'leia mais', 'saiba mais', 'clique aqui', 'acessar', 'download'
]


def scrape_fapesc_calls():
    """Scrape public calls from FAPESC website with improved parsing."""
    calls = []
    seen_urls = set()
    seen_titles = set()

    session = requests.Session()
    session.headers.update(HEADERS)

    for url in FAPESC_URLS:
        try:
            logger.info(f"Buscando FAPESC: {url}")
            response = session.get(url, timeout=30, verify=False)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Strategy 1: Look for WordPress-style article/post structures
            found_items = _parse_wordpress_posts(soup)

            # Strategy 2: Look for list items with links
            if not found_items:
                found_items = _parse_list_items(soup)

            # Strategy 3: Look for content divs with specific classes
            if not found_items:
                found_items = _parse_content_divs(soup)

            # Strategy 4: Fallback to enhanced link parsing
            if not found_items:
                found_items = _parse_enhanced_links(soup)

            for item in found_items:
                # Deduplicate
                if item['url'] in seen_urls:
                    continue
                if item['title'] in seen_titles:
                    continue

                # Validate
                if not _is_valid_call(item['title']):
                    continue

                seen_urls.add(item['url'])
                seen_titles.add(item['title'])

                call = {
                    'source': 'FAPESC',
                    'title': item['title'][:500],
                    'theme': _extract_theme(item['title']),
                    'description': item.get('description', item['title'])[:1000],
                    'publication_date': item.get('date', ''),
                    'deadline': item.get('deadline', _extract_deadline(item['title'])),
                    'funding_source': 'FAPESC - Fundação de Amparo à Pesquisa e Inovação de SC',
                    'target_audience': 'Pesquisadores, ICTs e Empresas de SC',
                    'url': item['url'],
                }

                calls.append(call)
                logger.info(f"FAPESC encontrada: {item['title'][:60]}...")

        except Exception as e:
            logger.error(f"Erro ao buscar FAPESC ({url}): {e}")
            continue

    logger.info(f"FAPESC: Total de {len(calls)} chamadas encontradas")
    return calls


def _parse_wordpress_posts(soup):
    """Parse WordPress-style post structures."""
    items = []

    # Try various WordPress selectors
    selectors = [
        'article.post', 'article.type-post', 'div.post',
        'div.post-item', 'div.entry', 'div.hentry',
        'li.post', 'div.blog-post', 'div.chamada-item'
    ]

    for selector in selectors:
        posts = soup.select(selector)
        if posts:
            for post in posts:
                item = _extract_post_data(post)
                if item:
                    items.append(item)
            if items:
                break

    return items


def _parse_list_items(soup):
    """Parse list-based structures."""
    items = []

    # Look for ul/ol with relevant content
    lists = soup.select('ul.chamadas, ul.editais, ol.chamadas, div.lista-chamadas ul')
    if not lists:
        lists = soup.select('main ul, article ul, div.content ul, div.entry-content ul')

    for ul in lists:
        for li in ul.find_all('li', recursive=False):
            link = li.find('a', href=True)
            if link:
                text = link.get_text(strip=True)
                href = link['href']
                if len(text) >= 20:
                    url = href if href.startswith('http') else FAPESC_BASE_URL + href
                    items.append({
                        'title': text,
                        'url': url,
                        'description': li.get_text(strip=True)
                    })

    return items


def _parse_content_divs(soup):
    """Parse content container structures."""
    items = []

    # Common content container selectors
    selectors = [
        'div.elementor-widget-container',
        'div.entry-content',
        'div.post-content',
        'div.page-content',
        'main.site-main',
        'div.content-area'
    ]

    for selector in selectors:
        containers = soup.select(selector)
        for container in containers:
            # Look for headings followed by links
            headings = container.find_all(['h2', 'h3', 'h4'])
            for heading in headings:
                link = heading.find('a', href=True)
                if link:
                    text = link.get_text(strip=True)
                    href = link['href']
                    if len(text) >= 20:
                        url = href if href.startswith('http') else FAPESC_BASE_URL + href
                        items.append({
                            'title': text,
                            'url': url
                        })

    return items


def _parse_enhanced_links(soup):
    """Enhanced link parsing with context awareness."""
    items = []

    # Find main content area first
    main_content = soup.find('main') or soup.find('article') or soup.find('div', class_=re.compile(r'content|main|entry'))

    if not main_content:
        main_content = soup

    all_links = main_content.find_all('a', href=True)

    for link in all_links:
        text = link.get_text(strip=True)
        href = link['href']

        # Skip short text
        if not text or len(text) < 25:
            continue

        # Skip non-content URLs
        if any(x in href.lower() for x in ['#', 'javascript:', 'mailto:', 'tel:', '/tag/', '/author/', '/wp-admin']):
            continue

        # Check parent context - skip nav/menu items
        parent = link.find_parent(['nav', 'header', 'footer', 'aside'])
        if parent:
            continue

        # Check for valid call indicators in URL or text
        if _is_valid_call(text) or _is_valid_call(href):
            url = href if href.startswith('http') else FAPESC_BASE_URL + href

            # Try to get surrounding context for description
            parent_elem = link.find_parent(['p', 'div', 'li'])
            description = parent_elem.get_text(strip=True) if parent_elem else text

            items.append({
                'title': text,
                'url': url,
                'description': description[:500]
            })

    return items


def _extract_post_data(post):
    """Extract data from a WordPress post element."""
    # Find title link
    title_elem = post.find(['h1', 'h2', 'h3'], class_=re.compile(r'title|heading'))
    if not title_elem:
        title_elem = post.find(['h1', 'h2', 'h3'])

    if not title_elem:
        return None

    link = title_elem.find('a', href=True) or post.find('a', href=True)
    if not link:
        return None

    title = title_elem.get_text(strip=True) or link.get_text(strip=True)
    href = link['href']

    if len(title) < 15:
        return None

    url = href if href.startswith('http') else FAPESC_BASE_URL + href

    # Try to find date
    date_elem = post.find(['time', 'span', 'div'], class_=re.compile(r'date|time|data'))
    date_text = ''
    if date_elem:
        date_text = date_elem.get_text(strip=True)

    # Try to find excerpt/description
    excerpt_elem = post.find(['p', 'div'], class_=re.compile(r'excerpt|summary|descr'))
    if not excerpt_elem:
        excerpt_elem = post.find('p')
    description = excerpt_elem.get_text(strip=True) if excerpt_elem else title

    return {
        'title': title,
        'url': url,
        'date': date_text,
        'description': description
    }


def _is_valid_call(text):
    """Check if text indicates a valid public call."""
    text_lower = text.lower()

    # Must contain at least one valid keyword
    has_valid = any(kw in text_lower for kw in VALID_KEYWORDS)
    if not has_valid:
        return False

    # Must not contain exclusion keywords
    has_exclude = any(kw in text_lower for kw in EXCLUDE_KEYWORDS)
    if has_exclude:
        return False

    return True


def _extract_deadline(text):
    """Extract deadline date from text if present."""
    # Look for date patterns
    patterns = [
        r'até\s*(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4})',
        r'prazo[:\s]*(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4})',
        r'encerr\w*[:\s]*(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4})',
        r'(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4})',
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    return ''


def _extract_theme(title):
    """Extract theme from the title."""
    themes = {
        'saúde': 'Saúde',
        'saude': 'Saúde',
        'agro': 'Agropecuária',
        'energia': 'Energia',
        'defesa': 'Defesa Nacional',
        'soberania': 'Defesa Nacional',
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
        'turismo': 'Turismo',
        'mar': 'Economia do Mar',
        'oceano': 'Economia do Mar',
        'pesca': 'Pesca e Aquicultura',
        'tecnologia': 'Tecnologia',
        'sinapse': 'Startups',
        'centelha': 'Startups',
        'tecnova': 'Inovação',
        'capacitação': 'Capacitação',
    }

    title_lower = title.lower()
    for key, value in themes.items():
        if key in title_lower:
            return value

    return 'Ciência, Tecnologia e Inovação'
