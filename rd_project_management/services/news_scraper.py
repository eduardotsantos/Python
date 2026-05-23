"""Service to fetch news from FINEP and FAPESC for the login page."""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
}


def fetch_finep_news(limit=4):
    """Fetch latest news from FINEP website."""
    news = []
    try:
        url = 'https://www.finep.gov.br/noticias'
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        # Find news items
        articles = soup.find_all('div', class_='item-page') or soup.find_all('article') or soup.find_all('div', class_='blog-item')

        if not articles:
            # Try alternative selectors
            articles = soup.find_all('div', class_='noticia') or soup.find_all('li', class_='item')

        for article in articles[:limit]:
            try:
                # Try to find title
                title_tag = article.find(['h2', 'h3', 'h4', 'a'])
                if not title_tag:
                    continue

                title = title_tag.get_text(strip=True)
                if not title or len(title) < 10:
                    continue

                # Try to find link
                link_tag = article.find('a', href=True)
                link = link_tag['href'] if link_tag else ''
                if link and not link.startswith('http'):
                    link = 'https://www.finep.gov.br' + link

                # Try to find date
                date_tag = article.find(['time', 'span'], class_=re.compile(r'date|data|time'))
                date_str = date_tag.get_text(strip=True) if date_tag else ''

                # Try to find summary
                summary_tag = article.find('p') or article.find('div', class_='intro')
                summary = summary_tag.get_text(strip=True)[:150] if summary_tag else ''

                news.append({
                    'title': title[:100],
                    'link': link,
                    'date': date_str,
                    'summary': summary,
                    'source': 'FINEP',
                    'image': 'https://www.finep.gov.br/images/logo-finep.png'
                })
            except Exception:
                continue

    except Exception as e:
        print(f"Error fetching FINEP news: {e}")

    # Return default news if scraping fails
    if not news:
        news = [
            {
                'title': 'FINEP lança novos programas de apoio à inovação',
                'link': 'https://www.finep.gov.br/noticias',
                'date': '',
                'summary': 'Financiadora de Estudos e Projetos amplia recursos para P&D',
                'source': 'FINEP',
                'image': ''
            },
            {
                'title': 'Recursos para startups e empresas inovadoras',
                'link': 'https://www.finep.gov.br/noticias',
                'date': '',
                'summary': 'Novas linhas de crédito disponíveis para projetos de inovação',
                'source': 'FINEP',
                'image': ''
            }
        ]

    return news[:limit]


def fetch_fapesc_news(limit=4):
    """Fetch latest news from FAPESC website."""
    news = []
    try:
        url = 'https://fapesc.sc.gov.br/category/noticias/'
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        # Find news items
        articles = soup.find_all('article') or soup.find_all('div', class_='post') or soup.find_all('div', class_='noticia')

        for article in articles[:limit]:
            try:
                # Try to find title
                title_tag = article.find(['h2', 'h3', 'h4'])
                if not title_tag:
                    title_tag = article.find('a')
                if not title_tag:
                    continue

                title = title_tag.get_text(strip=True)
                if not title or len(title) < 10:
                    continue

                # Try to find link
                link_tag = article.find('a', href=True)
                link = link_tag['href'] if link_tag else ''

                # Try to find image
                img_tag = article.find('img', src=True)
                image = img_tag['src'] if img_tag else ''

                # Try to find date
                date_tag = article.find(['time', 'span'], class_=re.compile(r'date|data|time|posted'))
                date_str = date_tag.get_text(strip=True) if date_tag else ''

                # Try to find summary
                summary_tag = article.find('p') or article.find('div', class_='excerpt')
                summary = summary_tag.get_text(strip=True)[:150] if summary_tag else ''

                news.append({
                    'title': title[:100],
                    'link': link,
                    'date': date_str,
                    'summary': summary,
                    'source': 'FAPESC',
                    'image': image
                })
            except Exception:
                continue

    except Exception as e:
        print(f"Error fetching FAPESC news: {e}")

    # Return default news if scraping fails
    if not news:
        news = [
            {
                'title': 'FAPESC apoia pesquisa e inovação em Santa Catarina',
                'link': 'https://fapesc.sc.gov.br',
                'date': '',
                'summary': 'Fundação investe em projetos de desenvolvimento científico e tecnológico',
                'source': 'FAPESC',
                'image': ''
            },
            {
                'title': 'Chamadas públicas abertas para pesquisadores',
                'link': 'https://fapesc.sc.gov.br/chamadas-abertas/',
                'date': '',
                'summary': 'Oportunidades de financiamento para projetos de P&D',
                'source': 'FAPESC',
                'image': ''
            }
        ]

    return news[:limit]


def get_innovation_news(finep_limit=3, fapesc_limit=3):
    """Get combined news from FINEP and FAPESC."""
    finep_news = fetch_finep_news(finep_limit)
    fapesc_news = fetch_fapesc_news(fapesc_limit)

    # Interleave news from both sources
    combined = []
    max_len = max(len(finep_news), len(fapesc_news))

    for i in range(max_len):
        if i < len(finep_news):
            combined.append(finep_news[i])
        if i < len(fapesc_news):
            combined.append(fapesc_news[i])

    return combined
