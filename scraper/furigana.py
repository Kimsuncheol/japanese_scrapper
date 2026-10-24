"""Align source readings to kanji runs without guessing pronunciations."""
import re
import unicodedata
from functools import lru_cache

from markupsafe import Markup, escape

KANJI = re.compile(r'[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff々〆]+')
PARTS = re.compile(r'[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff々〆]+|[^\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff々〆]+')
SPEAKER = re.compile(r'^([A-ZＡ-Ｚ][\s:：]+)')


def normalize(text):
    text = unicodedata.normalize('NFKC', text)
    text = ''.join(chr(ord(c) - 0x60) if '\u30a1' <= c <= '\u30f6' else c for c in text)
    return ''.join(c for c in text if c.isalnum() or c in 'ー々〆、。!?…')


def furigana(text, reading=''):
    """Return escaped ruby HTML only when kana anchors give a unique alignment.

    Consecutive kanji form a word-sized ruby base. Kana and punctuation remain
    plain text. Missing or ambiguous readings leave the original text intact.
    """
    text, reading = str(text), str(reading or '')
    if not reading or not KANJI.search(text):
        return escape(text)
    speaker = SPEAKER.match(text)
    prefix = speaker.group() if speaker else ''
    body = text[len(prefix):]
    reading = SPEAKER.sub('', reading)
    parts = PARTS.findall(body)
    target = normalize(reading)
    if len(target) > 1000 or len(parts) > 100:
        return escape(text)

    @lru_cache(maxsize=None)
    def align(index, offset):
        if index == len(parts):
            return ((),) if offset == len(target) else ()
        part = parts[index]
        results = []
        if KANJI.fullmatch(part):
            for end in range(offset + 1, len(target) + 1):
                ruby = target[offset:end]
                if not all('\u3041' <= c <= '\u3096' or c == 'ー' for c in ruby):
                    break
                for tail in align(index + 1, end):
                    results.append((ruby,) + tail)
                    if len(results) == 2:
                        return tuple(results)
        else:
            literal = normalize(part)
            if target.startswith(literal, offset):
                results = [(None,) + tail for tail in align(index + 1, offset + len(literal))]
        return tuple(results)

    solutions = align(0, 0)
    if len(solutions) != 1:
        return escape(text)
    html = [escape(prefix)]
    for part, ruby in zip(parts, solutions[0]):
        if ruby:
            html.append(Markup('<ruby>{}<rp>(</rp><rt>{}</rt><rp>)</rp></ruby>').format(escape(part), escape(ruby)))
        else:
            html.append(escape(part))
    return Markup('').join(html)
