from copy import deepcopy
from scraper.lesson_notes import organize_lesson
from scraper.models import Lesson


def test_legacy_glossary_moves_without_losing_content():
    lead = {'japanese':'虹がかかる', 'reading':'にじがかかる', 'translation':'무지개가 뜨다',
            'examples':[{'japanese':'ほら、虹がかかっていますよ。'}]}
    term = {'japanese':'本当','reading':'ほんとう','translation':'정말, 진짜','explanation':'','examples':[]}
    second_lesson = {'japanese':'別の表現', 'explanation':'A real teaching explanation', 'examples':[]}
    original = {'expressions':[lead, term, second_lesson], 'notes':['existing note']}
    before = deepcopy(original)
    organized = organize_lesson(original)
    assert original == before
    assert organized['expressions'] == [lead, second_lesson]
    assert organized['vocabulary'] == [term]
    assert organized['notes'][0] == 'existing note'
    assert '本当 (ほんとう) — 정말, 진짜' in organized['notes']
    assert organize_lesson(organized) == organized


def test_new_glossary_and_empty_legacy_notes_supported():
    lesson = Lesson.model_validate({'expressions':[{'japanese':'虹がかかる'}],
        'vocabulary':[{'japanese':'二重','reading':'にじゅう','translation':'이중'}]})
    assert lesson.vocabulary[0].translation == '이중'
    assert Lesson.model_validate({'expressions':[{'japanese':'虹'}]}).vocabulary == []


def test_glossary_renders_only_inside_lesson_notes(tmp_path, monkeypatch):
    from app import app
    from scraper import storage
    monkeypatch.setenv('DATA_PATH',str(tmp_path / 'articles.json'))
    article = {'id':'notes','title':'lesson','date':'2026-11-02','status':'ready','url':'https://www.chosun.com/source',
        'images':[], 'lesson':{'expressions':[{'japanese':'虹がかかる','reading':'にじがかかる','translation':'무지개가 뜨다','examples':[]}],
        'vocabulary':[{'japanese':'本当','reading':'ほんとう','translation':'정말, 진짜'}], 'notes':['preserved note']}}
    storage.write({'articles':[article], 'coverage':{}})
    client = app.test_client()
    html = client.get('/articles/notes').get_data(as_text=True)
    main, notes = html.split('<section class="lesson-notes"',1)
    assert '本当' not in main
    assert '<h2 id="lesson-notes-heading">Lesson notes</h2>' in notes
    assert '<ruby>本当<rp>(</rp><rt>ほんとう</rt>' in notes
    assert '정말, 진짜' in notes and 'preserved note' in notes
    assert client.get('/api/articles/notes').json['lesson']['vocabulary'][0]['japanese']=='本当'


def test_notes_only_client_receives_glossary_and_web_does_not_duplicate(tmp_path, monkeypatch):
    from scraper import storage
    from app import app
    lesson = organize_lesson({'expressions':[{'japanese':'虹がかかる'}],
        'vocabulary':[{'japanese':'本当','reading':'ほんとう','translation':'정말, 진짜'}],
        'notes':['issue 5036']})
    assert lesson['notes'] == ['issue 5036','本当 (ほんとう) — 정말, 진짜']
    assert organize_lesson(lesson) == lesson
    monkeypatch.setenv('DATA_PATH',str(tmp_path/'archive.json'))
    storage.write({'coverage':{},'articles':[{'id':'compat','date':'2026-11-02','title':'lesson',
        'status':'ready','url':'https://www.chosun.com/source','images':[],'lesson':lesson}]})
    client=app.test_client()
    assert client.get('/api/articles/compat').json['lesson']['notes'] == lesson['notes']
    html=client.get('/articles/compat').get_data(as_text=True)
    assert html.count('정말, 진짜') == 1
    assert 'issue 5036' in html
