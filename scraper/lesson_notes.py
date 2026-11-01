"""Organize legacy standalone glossary entries without discarding any text."""
from copy import deepcopy

from .models import Lesson


def glossary_note(term):
    text = term['japanese']
    if term.get('reading'):
        text += ' (' + term['reading'] + ')'
    for field in ('translation', 'explanation'):
        if term.get(field):
            text += ' — ' + term[field]
    return text


def plain_notes(lesson):
    """Hide compatibility copies when the website renders structured glossary."""
    generated = {glossary_note(term) for term in lesson.get('vocabulary', [])}
    return [note for note in lesson.get('notes', []) if note not in generated]


def organize_lesson(lesson):
    result = deepcopy(lesson)
    expressions = result['expressions']
    vocabulary = result.get('vocabulary', [])
    main = []
    for index, expression in enumerate(expressions):
        # Keep the lead expression and any entry with teaching content/dialogue.
        # Legacy OCR frequently stored bare footer glossary entries as expressions.
        if index == 0 or expression.get('examples') or expression.get('explanation'):
            main.append(expression)
        else:
            vocabulary.append(expression)
    result['expressions'] = main
    result['vocabulary'] = vocabulary
    notes = list(result.get('notes', []))
    for term in vocabulary:
        note = glossary_note(term)
        if note not in notes:
            notes.append(note)
    result['notes'] = notes
    Lesson.model_validate(result)
    return result


def main():
    from . import storage
    data = storage.read()
    changed = moved = 0
    for article in data['articles']:
        if article.get('status') != 'ready':
            continue
        old = article['lesson']
        organized = organize_lesson(old)
        if organized != old:
            moved += len(old['expressions']) - len(organized['expressions'])
            article['lesson'] = organized
            changed += 1
    if changed:
        storage.write(data)
    print(f'Organized {changed} lessons; moved {moved} standalone terms to lesson notes.', flush=True)


if __name__ == '__main__':
    main()
