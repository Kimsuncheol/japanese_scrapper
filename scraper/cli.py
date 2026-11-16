import argparse
from datetime import datetime
from dotenv import load_dotenv

from . import storage
from .source import SEOUL, discover


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description='Discover Japanese lessons, optionally transcribing the newest article')
    parser.add_argument('--discover-only', action='store_true', help='Discover articles without model calls (the default)')
    parser.add_argument('--transcribe-latest', action='store_true', help='Transcribe only the newest discovered lesson using the configured model')
    args = parser.parse_args()
    if args.discover_only and args.transcribe_latest:
        parser.error('Choose discovery-only or transcribe-latest')
    data = storage.read()
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
    if args.transcribe_latest and data['articles']:
        latest = data['articles'][0]
        if latest.get('status') != 'ready':
            from .batch import process
            result = process(data, [latest], workers=1)
            if result['failures']:
                raise SystemExit(1)


if __name__ == '__main__':
    main()
