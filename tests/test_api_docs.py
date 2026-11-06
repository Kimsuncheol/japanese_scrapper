from pathlib import Path
from app import app


def test_documentation_renders_source_tables_and_code():
    response = app.test_client().get('/docs')
    assert response.status_code == 200
    assert response.mimetype == 'text/html'
    html = response.get_data(as_text=True)
    assert '<h1>API reference</h1>' in html
    assert '<table>' in html and '<pre><code' in html
    assert '/api/articles' in html
    assert 'vocabulary' in html
    assert 'View Markdown source' in html


def test_docs_uses_current_file_and_escapes_raw_html(monkeypatch):
    original = Path.read_text
    def source(path, *args, **kwargs):
        if path.name == 'API.md':
            return '# Updated reference\n\n<script>alert(1)</script>'
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'read_text', source)
    html = app.test_client().get('/docs').get_data(as_text=True)
    assert '<h1>Updated reference</h1>' in html
    assert '<script>' not in html and '&lt;script&gt;' in html
