"""Mirror validated lesson records into the JLPT practice Firebase project.

The public Flask API continues to serve the JSON snapshot. This writer uses
Application Default Credentials (local ADC or GitHub Workload Identity).
"""
import argparse
import hashlib
import json
from collections import Counter

from google.cloud import firestore

from . import storage
from .models import Lesson
from .lesson_notes import organize_lesson

PROJECT = 'jlpt-practice-20a4e'
COLLECTION = 'japanese_lessons'
METADATA = 'japanese_scraper/archive'
BATCH_SIZE = 100


def digest(article):
    return hashlib.sha256(json.dumps(article, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':')).encode()).hexdigest()


def sync(data, client=None):
    client = client if client is not None else firestore.Client(project=PROJECT)
    collection = client.collection(COLLECTION)
    # Read only sync headers, not thousands of full lesson payloads.
    existing = {doc.id: doc.to_dict() for doc in collection.select(
        ['_sync_hash', 'url', 'processed_at']).stream()}
    ready = [a for a in data['articles'] if a.get('status') == 'ready']
    updated = skipped = newer = 0
    batch = client.batch()
    queued = 0
    for article in ready:
        article = {**article, 'lesson': organize_lesson(article['lesson'])}
        Lesson.model_validate(article.get('lesson'))
        article_id = article['id']
        if not article_id or '/' in article_id or article_id in {'.', '..'}:
            raise ValueError('Invalid publisher article ID')
        previous = existing.get(article_id, {})
        if previous.get('url') and previous['url'] != article['url']:
            raise ValueError('Firestore ID belongs to a different source URL')
        source_hash = digest(article)
        if previous.get('_sync_hash') == source_hash:
            skipped += 1
            continue
        if previous.get('processed_at', '') > article.get('processed_at', ''):
            newer += 1
            continue
        # Never overwrite other clients' extra fields or delete documents.
        record = {**article, '_sync_hash': source_hash,
                  '_synced_at': firestore.SERVER_TIMESTAMP}
        if len(json.dumps(article, ensure_ascii=False).encode()) > 900_000:
            raise ValueError('Lesson exceeds safe Firestore document size')
        batch.set(collection.document(article_id), record, merge=True)
        queued += 1
        updated += 1
        if queued == BATCH_SIZE:
            batch.commit()
            batch, queued = client.batch(), 0
    if queued:
        batch.commit()
    counts = Counter(a.get('status', 'pending') for a in data['articles'])
    summary = {'project': PROJECT, 'collection': COLLECTION, 'ready': len(ready),
               'updated': updated, 'unchanged': skipped, 'newer_in_firestore': newer}
    client.document(METADATA).set({
        'coverage': data.get('coverage', {}), 'counts': dict(counts),
        'discovered': len(data['articles']), 'ready': len(ready),
        'source': 'https://github.com/Kimsuncheol/japanese_scrapper',
        'last_sync': firestore.SERVER_TIMESTAMP,
    }, merge=True)
    return summary


def main():
    parser = argparse.ArgumentParser(description='Save validated Japanese lessons to Firebase Firestore')
    parser.parse_args()
    print(json.dumps(sync(storage.read())), flush=True)


if __name__ == '__main__':
    main()
