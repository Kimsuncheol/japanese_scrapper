import argparse
import json
from pathlib import Path
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
    parser.add_argument('--workers', type=int, default=1, help='Concurrent transcriptions (1–4)')
    parser.add_argument('--max-seconds', type=int, default=0, help='Stop submitting work after this duration; 0 is unlimited')
    parser.add_argument('--summary', help='Write batch summary JSON for workflow continuation')
    args = parser.parse_args()
    if not 1 <= args.workers <= 4 or args.max_seconds < 0:
        parser.error('workers must be 1–4 and max-seconds must be nonnegative')
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
    pending = [a for a in data['articles'] if a.get('status') != 'ready' and (not args.url or a['url'] == args.url)]
    if args.url and not pending:
        print('Article is already ready or was not found in the archive.', flush=True)
    # New pending entries precede failures so a broken image cannot block backfill.
    pending.sort(key=lambda a: (a.get('status') == 'error', a.get('attempts', 0)))
    from .batch import process
    summary = process(data, pending[:args.limit or None], args.workers, args.max_seconds)
    if args.summary:
        Path(args.summary).write_text(json.dumps(summary))
    print('Batch summary:', json.dumps(summary), flush=True)
    if summary['failures']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
