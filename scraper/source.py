"""Read the public section feed and full-size article content images."""
import json
import re
from datetime import datetime
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

ROOT = 'https://www.chosun.com'
SECTION = '/national/nie/japanese'
SEOUL = ZoneInfo('Asia/Seoul')
SESSION = requests.Session()
SESSION.headers['User-Agent'] = 'JapaneseStudyReader/1.0'
SESSION.mount('https://', HTTPAdapter(max_retries=Retry(
    total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])))


def get(url, **kwargs):
    response = SESSION.get(url, timeout=60, **kwargs)
    response.raise_for_status()
    return response


def embedded(html, name='globalContent'):
    marker = f'Fusion.{name}='
    if marker not in html:
        raise ValueError(f'Article has no {name} data')
    return json.JSONDecoder().raw_decode(html.split(marker, 1)[1])[0]


def discover():
    """Exhaust the feed; never infer an earliest date from the visible page."""
    offset, seen = 0, set()
    while True:
        query = dict(includeSections=SECTION, includeContentTypes='story',
                     excludeContentTypes='gallery, video', size=100, offset=offset)
        data = get(ROOT + '/pf/api/v3/content/fetch/story-feed', params={
            'query': json.dumps(query), '_website': 'chosun'}).json()
        items = data.get('content_elements', [])
        if not items:
            if offset < data.get('count', offset):
                raise ValueError('Feed ended before its reported count')
            break
        fresh = 0
        for item in items:
            url = urljoin(ROOT, item['canonical_url'])
            if url in seen:
                continue
            seen.add(url)
            fresh += 1
            date = datetime.fromisoformat(item['display_date'].replace('Z', '+00:00')).astimezone(SEOUL).date()
            if date <= datetime.now(SEOUL).date():
                yield {'id': item['_id'], 'url': url, 'date': date.isoformat(),
                       'title': item.get('headlines', {}).get('basic', ''), 'status': 'pending'}
        if not fresh:
            raise ValueError('Feed pagination repeated; archive is incomplete')
        next_offset = data.get('next')
        if next_offset is None:
            if offset + len(items) < data.get('count', 0):
                raise ValueError('Feed pagination stopped before its reported count')
            break
        offset = int(next_offset)


def article_images(url):
    parsed = urlparse(url)
    if parsed.scheme != 'https' or parsed.hostname != 'www.chosun.com':
        raise ValueError('Expected a Chosun article URL')
    content = embedded(get(url).text)
    images = []

    def walk(elements):
        for el in elements:
            if el.get('type') == 'image' and el.get('url'):
                images.append(el['url'])
            walk(el.get('content_elements', []))
    walk(content.get('content_elements', []))
    if not images:
        raise ValueError('No article-body images found')
    return list(dict.fromkeys(images))


def image_bytes(url):
    host = urlparse(url).hostname or ''
    if not (host.endswith('.arcpublishing.com') or host.endswith('.chosun.com')):
        raise ValueError('Unexpected image host')
    response = get(url)
    mime = response.headers.get('Content-Type', '').split(';')[0]
    if mime not in {'image/jpeg', 'image/png', 'image/webp', 'image/gif'}:
        raise ValueError('Unsupported image content type')
    if len(response.content) > 20_000_000:
        raise ValueError('Image exceeds 20 MB')
    return response.content, mime
