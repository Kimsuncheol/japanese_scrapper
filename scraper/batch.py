"""Bounded concurrent processing, with all persistence owned by the caller thread."""
import os
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import datetime

from . import storage
from .source import SEOUL, article_images


def transcribe(article):
    from .vision import extract
    images = article_images(article['url'])
    article['images'] = images
    return images, extract(images)


def process(data, pending, workers=1, max_seconds=0):
    started = time.monotonic()
    completed = failures = 0
    blocked = False
    iterator = iter(pending)
    active = {}

    def submit(pool):
        if blocked or (max_seconds and time.monotonic() - started >= max_seconds):
            return False
        article = next(iterator, None)
        if article is None:
            return False
        article['attempts'] = article.get('attempts', 0) + 1
        active[pool.submit(transcribe, article)] = article
        return True

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for _ in range(workers):
            submit(pool)
        while active:
            done, _ = wait(active, return_when=FIRST_COMPLETED)
            for future in done:
                article = active.pop(future)
                try:
                    images, lesson = future.result()
                    article.update(images=images, lesson=lesson, status='ready',
                                   model=os.getenv('OLLAMA_MODEL', 'gemma4:31b'),
                                   processed_at=datetime.now(SEOUL).isoformat())
                    article.pop('error', None)
                    completed += 1
                    print('Ready:', article['date'], article['id'], flush=True)
                except Exception as exc:
                    article.update(status='error', error=type(exc).__name__)
                    failures += 1
                    code = getattr(exc, 'status_code', None)
                    response = getattr(exc, 'response', None)
                    code = code or getattr(response, 'status_code', None)
                    # Stop on model quota/auth failures instead of failing the entire archive.
                    if code in {401, 403, 429}:
                        blocked = True
                    print('Failed:', article['id'], type(exc).__name__, 'status', code, flush=True)
                storage.write(data)
            for _ in done:
                submit(pool)
    return {'completed': completed, 'failures': failures, 'blocked': blocked,
            'remaining': sum(a.get('status') != 'ready' for a in data['articles'])}
