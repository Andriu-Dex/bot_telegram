"""Bounded importer: only public course pages on the configured university host."""
import asyncio
import re
from urllib.parse import urljoin, urlparse
import httpx
from bs4 import BeautifulSoup, Comment
from sqlalchemy import select
from .models import Course, now

BASE = 'https://ctt-talleresfisei.uta.edu.ec/'

def clean(html):
    soup = BeautifulSoup(html, 'html.parser')
    for node in soup.find_all(string=lambda t: isinstance(t, Comment)):
        node.extract()
    for node in soup(['script', 'style']):
        node.decompose()
    return soup

def parse_listing(html):
    soup = clean(html)
    items = {}
    for link in soup.select('a.h5[href]'):
        href = link['href']
        if not re.fullmatch(r'curso\d+\.php', href):
            continue
        card = link.parent
        text = card.get_text(' ', strip=True)
        hours = re.search(r'\d+\s*HORAS(?: TOTAL)?', text, re.I)
        status = 'CERRADO' if 'CERRADO' in text else 'ABIERTO' if 'ABIERTO' in text else 'DESCONOCIDO'
        url = urljoin(BASE, href)
        items[url] = dict(source_url=url, title=link.get_text(' ', strip=True), status=status, hours=hours.group() if hours else '')
    if not items:
        raise ValueError('El catálogo cambió de formato o no contiene cursos. No se modificaron los datos.')
    return list(items.values())

def parse_detail(html):
    soup = clean(html)
    title = soup.select_one('.tituloCurso')
    if not title:
        raise ValueError('Ficha sin título reconocido')
    sections = soup.select('.descripcion, .objetivos, .ubicacion, .pc-tab')
    text = '\n\n'.join(x.get_text('\n', strip=True) for x in sections)
    if len(text) < 80:
        raise ValueError('Ficha sin contenido suficiente')
    link = soup.select_one('.registro a[href], #inscripcion a[href]')
    registration = urljoin(BASE, link['href']) if link else ''
    if registration and urlparse(registration).scheme != 'https':
        registration = ''
    return dict(title=title.get_text(' ', strip=True), content=text[:24000], registration_url=registration)

async def fetch_catalog():
    async with httpx.AsyncClient(timeout=25, follow_redirects=False, headers={'User-Agent': 'CTT-Admissions/1.0 (catalog import)'}) as client:
        response = await client.get(BASE + 'course.php')
        response.raise_for_status()
        items = parse_listing(response.text)
        errors = []
        semaphore = asyncio.Semaphore(3)
        async def detail(item):
            async with semaphore:
                try:
                    result = await client.get(item['source_url'])
                    result.raise_for_status()
                    return {**item, **parse_detail(result.text)}
                except (httpx.HTTPError, ValueError):
                    errors.append(item['source_url'])
                    return None
        results = await asyncio.gather(*(detail(item) for item in items))
    return [r for r in results if r], errors

def store_catalog(db, items):
    changed = 0
    for item in items:
        existing = db.scalar(select(Course).where(Course.source_url == item['source_url']))
        if not existing:
            db.add(Course(**item))
            changed += 1
        else:
            existing.synced_at = now()
            if any(getattr(existing, k) != v for k, v in item.items()):
                # Keep the published version while an advisor reviews the proposal.
                existing.pending = item
                changed += 1
    db.flush()
    return changed
