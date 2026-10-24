import argparse
from datetime import datetime
from dotenv import load_dotenv

from . import storage
from .source import SEOUL, article_images, discover


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description='Discover and transcribe Japanese lesson articles')
    parser.add_argument('--discover-only', action='store_true')
    parser.add_argument('--skip-discovery', action='store_true', help='Process the existing local index')
    parser.add_argument('--limit', type=int, default=10, help='OCR batch size; 0 processes the entire backlog')
    parser.add_argument('--url', help='Process one article already in the discovered archive')
    args = parser.parse_args()
    if args.limit < 0:
        parser.error('--limit must be nonnegative')
    data = storage.read()
    if not args.skip_discovery:
        existing = {a['url']: a for a in data['articles']}
        count = 0
        for item in discover():
            existing.setdefault(item['url'], item)
            count += 1
        data['articles'] = sorted(existing.values(), key=lambda a: (a['date'], a['id']), reverse=True)
        dates = [a['date'] for a in data['articles']]
        data['coverage'] = {'discovered_at': datetime.now(SEOUL).isoformat(),
                            'first_date': min(dates) if dates else None,
                            'latest_date': max(dates) if dates else None, 'feed_count': count}
        storage.write(data)
        print(f'Discovered {count} articles; archive {data["coverage"]["first_date"]} → {data["coverage"]["latest_date"]}', flush=True)
    if args.discover_only:
        return
    from .vision import extract
    pending = [a for a in data['articles'] if a.get('status') != 'ready' and (not args.url or a['url'] == args.url)]
    if args.url and not pending:
        print('Article is already ready or was not found in the archive.', flush=True)
    # New pending entries precede failures so a broken image cannot block backfill.
    pending.sort(key=lambda a: (a.get('status') == 'error', a.get('attempts', 0)))
    failures = 0
    for article in pending[:args.limit or None]:
        article['attempts'] = article.get('attempts', 0) + 1
        try:
            article['images'] = article_images(article['url'])
            article['lesson'] = extract(article['images'])
            article.update(status='ready', model=__import__('os').getenv('OLLAMA_MODEL', 'gemma4:31b'),
                           processed_at=datetime.now(SEOUL).isoformat())
            article.pop('error', None)
            print('Ready:', article['date'], article['id'], flush=True)
        except Exception as exc:
            # Exception messages can contain request credentials; persist only the class.
            article.update(status='error', error=type(exc).__name__)
            failures += 1
            print('Failed:', article['id'], type(exc).__name__, flush=True)
        storage.write(data)
    if failures:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
