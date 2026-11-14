import argparse
from datetime import datetime
from dotenv import load_dotenv

from . import storage
from .source import SEOUL, discover


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description='Discover Japanese lesson articles without model calls')
    parser.add_argument('--discover-only', action='store_true', help='Discover articles (the default and only mode)')
    parser.parse_args()
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


if __name__ == '__main__':
    main()
