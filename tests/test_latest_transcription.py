import json
import sys

import pytest
import requests

from scraper import cli, storage, vision


def test_latest_transcription_never_processes_backlog(tmp_path, monkeypatch):
    from scraper import batch
    monkeypatch.setenv('DATA_PATH', str(tmp_path / 'archive.json'))
    old = {'id': 'old', 'url': 'https://www.chosun.com/old', 'date': '2026-11-13', 'status': 'error'}
    new = {'id': 'new', 'url': 'https://www.chosun.com/new', 'date': '2026-11-16', 'status': 'pending'}
    monkeypatch.setattr(cli, 'discover', lambda: iter([old, new]))
    calls = []
    monkeypatch.setattr(batch, 'process', lambda data, pending, **kwargs: calls.extend(pending) or {'failures': 0})
    monkeypatch.setattr(sys, 'argv', ['scraper', '--transcribe-latest'])
    cli.main()
    assert calls == [new]
    assert storage.read()['articles'][1] == old


def test_missing_model_key_never_downloads_images(monkeypatch):
    monkeypatch.delenv('OLLAMA_API_KEY', raising=False)
    monkeypatch.setattr(vision, 'image_bytes', lambda url: pytest.fail('No image fetch without credentials'))
    with pytest.raises(ValueError, match='required'):
        vision.extract(['image'])


def test_auth_failure_is_not_retried(monkeypatch):
    monkeypatch.setenv('OLLAMA_API_KEY', 'fixture-secret')
    monkeypatch.setattr(vision, 'image_bytes', lambda url: (b'fixture', 'image/jpeg'))
    calls = []
    def post(url, **kwargs):
        calls.append(url)
        response = requests.Response()
        response.status_code = 401
        return response
    monkeypatch.setattr(vision.requests, 'post', post)
    with pytest.raises(requests.HTTPError):
        vision.extract(['image'])
    assert len(calls) == 1


def test_invalid_schema_cannot_be_marked_ready(monkeypatch):
    monkeypatch.setenv('OLLAMA_API_KEY', 'fixture-secret')
    monkeypatch.setattr(vision, 'image_bytes', lambda url: (b'fixture', 'image/jpeg'))
    monkeypatch.setattr(vision.time, 'sleep', lambda _: None)
    def post(url, **kwargs):
        response = requests.Response()
        response.status_code = 200
        response._content = json.dumps({'message': {'content': '{"expressions": []}'}}).encode()
        return response
    monkeypatch.setattr(vision.requests, 'post', post)
    with pytest.raises(ValueError):
        vision.extract(['image'])
