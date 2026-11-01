"""Organize legacy standalone glossary entries without discarding any text."""
from copy import deepcopy

from .models import Lesson


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
