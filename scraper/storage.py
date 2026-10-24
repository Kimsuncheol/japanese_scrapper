import json
import os
from pathlib import Path


def path():
    return Path(os.getenv('DATA_PATH', 'data/articles.json'))


def read():
    file = path()
    return json.loads(file.read_text()) if file.exists() else {'articles': [], 'coverage': {}}


def write(data):
    file = path()
    file.parent.mkdir(parents=True, exist_ok=True)
    temporary = file.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(file)
