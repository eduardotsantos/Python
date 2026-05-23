"""Scraper for FAPESC public calls."""

import requests
from bs4 import BeautifulSoup
import logging
import re
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

FAPESC_URL = "https://fapesc.sc.gov.br/chamadas-abertas/"
FAPESC_BASE_URL = "https://fapesc.sc.gov.br"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
}


def scrape_fapesc_calls():
    """Scrape public calls from FAPESC website."""
    calls = []
    seen_titles = set()

    try:
        logger.info(f"Buscando chamadas FAPESC de: {FAPESC_URL}")

        session = requests.Session()
        session.headers.update(HEADERS)

        response = session.get(FAPESC_URL, timeout=30, verify=False)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Find all links that contain "EDITAL" or "CHAMADA" in text
        all_links = soup.find_all('a', href=True)

        for link in all_links:
            text = link.get_text(strip=True)
            href = link['href']

            # Skip empty or short text
            if not text or len(text) < 20:
                continue

            # Skip if already seen
            if text in seen_titles:
                continue

            # Only get links that look like public calls
            text_upper = text.upper()
            if not any(kw in text_upper for kw in ['EDITAL', 'CHAMADA', 'PROGRAMA', 'SELEÇÃO', 'BOLSA']):
                continue

            # Skip navigation/menu items
            if any(skip in text_upper for skip in ['MENU', 'VOLTAR', 'HOME', 'CONTATO', 'ACESSO', 'INFORMAÇÃO']):
                continue

            # Skip results/amendments
            if any(skip in text_upper for skip in ['RESULTADO', 'RETIFICAÇÃO', 'ERRATA', 'PRORROGAÇÃO']):
                continue

            seen_titles.add(text)

            # Build full URL
            url = href if href.startswith('http') else FAPESC_BASE_URL + href

            call = {
                'source': 'FAPESC',
                'title': text,
                'theme': _extract_theme(text),
                'description': text,
                'publication_date': '',
                'deadline': _extract_deadline(text),
                'funding_source': 'FAPESC - Fundação de Amparo à Pesquisa e Inovação de SC',
                'target_audience': 'Pesquisadores, ICTs e Empresas de SC',
                'url': url,
            }

            calls.append(call)
            logger.info(f"FAPESC encontrada: {text[:60]}...")

        logger.info(f"FAPESC: Total de {len(calls)} chamadas encontradas")

    except Exception as e:
        logger.error(f"Erro ao buscar FAPESC: {e}")

    return calls


def _extract_deadline(text):
    """Extract deadline date from text if present."""
    # Look for date patterns
    date_match = re.search(r'(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4})', text)
    if date_match:
        return date_match.group(1)
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
    }

    title_lower = title.lower()
    for key, value in themes.items():
        if key in title_lower:
            return value

    return 'Ciência, Tecnologia e Inovação'
