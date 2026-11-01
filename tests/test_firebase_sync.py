from copy import deepcopy
from types import SimpleNamespace

import pytest
from scraper.firebase_sync import COLLECTION, METADATA, digest, sync


class Reference:
    def __init__(self, db, path):
        self.db, self.path = db, path

    def set(self, record, merge=False):
        self.db.docs.setdefault(self.path, {}).update(record)
        self.db.writes.append(self.path)


class Collection:
    def __init__(self, db):
        self.db = db

    def select(self, fields):
        return self

    def stream(self):
        for path, record in list(self.db.docs.items()):
            if path.startswith(COLLECTION + '/'):
                yield SimpleNamespace(id=path.split('/')[1], to_dict=lambda record=record: deepcopy(record))

    def document(self, article_id):
        return Reference(self.db, COLLECTION + '/' + article_id)


class Client:
    def __init__(self):
        self.docs, self.writes, self.commits = {}, [], 0

    def collection(self, name):
        assert name == COLLECTION
        return Collection(self)

    def document(self, path):
        assert path == METADATA
        return Reference(self, path)

    def batch(self):
        db = self
        class Batch:
            def __init__(self):
                self.pending = []
            def set(self, ref, record, merge):
                assert merge
                self.pending.append((ref, record))
            def commit(self):
                db.commits += 1
                for ref, record in self.pending:
                    ref.set(record, merge=True)
        return Batch()


def archive():
    return {'coverage': {'first_date':'2003-11-11'}, 'articles': [
        {'id':'ready','url':'https://www.chosun.com/ready','status':'ready',
         'processed_at':'2026-11-01T01:00:00+09:00',
         'lesson':{'expressions':[{'japanese':'日本語','reading':'にほんご'}]}},
        {'id':'pending','status':'pending'}, {'id':'failed','status':'error'}]}


def test_only_validated_ready_lessons_and_idempotent_sync():
    db, data = Client(), archive()
    db.docs['users/existing'] = {'keep':'untouched'}
    first = sync(data, db)
    assert first['updated'] == 1
    assert db.docs[COLLECTION+'/ready']['lesson']['expressions'] == data['articles'][0]['lesson']['expressions']
    assert db.docs['users/existing'] == {'keep':'untouched'}
    assert db.docs[METADATA]['counts'] == {'ready':1,'pending':1,'error':1}
    assert sync(data, db)['unchanged'] == 1
    assert db.writes.count(COLLECTION+'/ready') == 1
    data['articles'][0]['lesson']['notes'] = ['note']
    assert sync(data, db)['updated'] == 1
    assert 'pending' not in [p.split('/')[-1] for p in db.docs]


def test_reject_invalid_lessons_and_collisions():
    db, data = Client(), archive()
    data['articles'][0]['lesson']['expressions'] = []
    with pytest.raises(ValueError):
        sync(data, db)
    assert not db.writes
    data = archive()
    db.docs[COLLECTION+'/ready'] = {'url':'https://different.example'}
    with pytest.raises(ValueError, match='different source'):
        sync(data, db)


def test_preserve_newer_firestore_record_and_unrelated_fields():
    db, data = Client(), archive()
    db.docs[COLLECTION+'/ready'] = {'processed_at':'2026-11-02T00:00:00+09:00'}
    assert sync(data, db)['newer_in_firestore'] == 1
    assert COLLECTION+'/ready' not in db.writes
    db.docs[COLLECTION+'/ready'] = {'custom_field':'keep'}
    sync(data, db)
    assert db.docs[COLLECTION+'/ready']['custom_field'] == 'keep'


def test_bounded_batch_commits():
    db, data = Client(), archive()
    ready = data['articles'][0]
    data['articles'] = [{**deepcopy(ready),'id':str(i)} for i in range(205)]
    result = sync(data, db)
    assert db.commits == 3 and result['updated'] == 205
