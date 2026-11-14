import json
import pytest
from app import app
from scraper.models import Lesson
from scraper.source import embedded, article_images
from scraper import source, storage


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('DATA_PATH', str(tmp_path / 'articles.json'))
    storage.write({'articles': [{'id': str(i), 'date': '2026-10-23', 'title': '<script>alert(1)</script>',
                                'url': 'https://www.chosun.com/example', 'status': 'ready'} for i in range(21)],
                   'coverage': {}})
    app.config['TESTING'] = True
    return app.test_client()


def test_pagination(client):
    first = client.get('/api/articles').json
    second = client.get('/api/articles?page=2').json
    last = client.get('/api/articles?page=3').json
    assert len(first['articles']) == len(second['articles']) == 10
    assert len(last['articles']) == 1
    assert first['articles'][0]['id'] != second['articles'][0]['id']
    assert client.get('/?page=0').status_code == 404
    assert client.get('/?page=4').status_code == 404
    assert client.get('/?page=no').status_code == 400


def test_filters_and_escaping(client):
    assert client.get('/api/articles?status=pending').json['total'] == 0
    assert client.get('/api/articles?q=missing').json['total'] == 0
    assert b'&lt;script&gt;' in client.get('/').data
    assert client.get('/articles/0').status_code == 200
    assert client.get('/articles/missing').status_code == 404


def test_image_extraction_ignores_promos(monkeypatch):
    data = {'content_elements': [{'type': 'image', 'url': 'full.jpg'}],
            'promo_items': {'basic': {'type': 'image', 'url': 'cropped.jpg'}}}
    class Response:
        text = 'Fusion.globalContent=' + json.dumps(data) + ';Fusion.other={}'
    monkeypatch.setattr(source, 'get', lambda url: Response())
    assert article_images('https://www.chosun.com/article') == ['full.jpg']
    with pytest.raises(ValueError):
        article_images('https://evil.example/article')


def test_empty_transcription_rejected():
    with pytest.raises(ValueError):
        Lesson.model_validate({'expressions': []})


def test_discovery_pagination_and_korean_date(monkeypatch):
    calls = []
    def fake_get(url, params):
        offset = json.loads(params['query'])['offset']
        calls.append(offset)
        class Response:
            def json(self):
                return {'content_elements': [{'_id':str(offset), 'canonical_url':f'/site/{offset}',
                         'display_date':'2026-10-22T15:34:00Z', 'headlines':{'basic':'lesson'}}],
                        'next':1 if offset == 0 else None, 'count':2}
        return Response()
    monkeypatch.setattr(source,'get',fake_get)
    items = list(source.discover())
    assert calls == [0,1]
    assert len(items) == 2 and items[0]['date'] == '2026-10-23'


def test_repeated_feed_rejected(monkeypatch):
    class Response:
        def json(self):
            return {'content_elements':[{'_id':'1','canonical_url':'/same',
                    'display_date':'2026-10-22T15:34:00Z'}], 'next':1, 'count':100}
    monkeypatch.setattr(source,'get',lambda *a,**k:Response())
    with pytest.raises(ValueError, match='repeated'):
        list(source.discover())


def test_discovery_preserves_lessons_and_leaves_new_articles_pending(tmp_path, monkeypatch):
    from scraper import cli
    import sys
    monkeypatch.setenv('DATA_PATH', str(tmp_path / 'archive.json'))
    ready = {'id': 'old', 'url': 'https://www.chosun.com/old', 'date': '2026-10-22',
             'status': 'ready', 'model': 'historical-model', 'lesson': {'expressions': [{'japanese': 'はい'}]}}
    storage.write({'articles': [ready], 'coverage': {}})
    new = {'id': 'new', 'url': 'https://www.chosun.com/new', 'date': '2026-10-23', 'status': 'pending'}
    monkeypatch.setattr(cli, 'discover', lambda: iter([ready, new]))
    monkeypatch.setattr(sys, 'argv', ['scraper'])
    cli.main()
    result = storage.read()
    assert result['articles'] == [new, ready]
    assert result['coverage']['feed_count'] == 2


def test_removed_transcription_options_rejected(monkeypatch):
    from scraper import cli
    import sys
    monkeypatch.setattr(sys, 'argv', ['scraper', '--limit', '0'])
    monkeypatch.setattr(cli, 'discover', lambda: pytest.fail('Must reject before discovery'))
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 2
