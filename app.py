import math
from flask import Flask, abort, jsonify, render_template, request
from dotenv import load_dotenv
from scraper.storage import read
from scraper.furigana import furigana

load_dotenv()
app = Flask(__name__)
app.jinja_env.filters["furigana"] = furigana


def listing():
    data = read()
    articles = data['articles']
    q = request.args.get('q', '').strip()
    status = request.args.get('status', 'ready')
    if status not in {'ready', 'pending', 'error', 'all'}:
        abort(400)
    selected = [a for a in articles if (status == 'all' or a.get('status') == status)
                and (not q or q.casefold() in (a['title'] + str(a.get('lesson', ''))).casefold())]
    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        abort(400)
    pages = max(1, math.ceil(len(selected) / 10))
    if page < 1 or page > pages:
        abort(404)
    return dict(articles=selected[(page-1)*10:page*10], page=page, pages=pages,
                total=len(selected), q=q, status=status, coverage=data.get('coverage', {}),
                ready=sum(a.get('status') == 'ready' for a in articles), discovered=len(articles))


@app.get('/')
def index():
    return render_template('index.html', **listing())


@app.get('/articles/<article_id>')
def detail(article_id):
    article = next((a for a in read()['articles'] if a['id'] == article_id), None)
    if article is None:
        abort(404)
    return render_template('detail.html', article=article)


@app.get('/api/articles')
def api_articles():
    return jsonify(listing())


@app.get('/api/articles/<article_id>')
def api_article(article_id):
    article = next((a for a in read()['articles'] if a['id'] == article_id), None)
    if article is None:
        abort(404)
    return jsonify(article)


@app.get('/health')
def health():
    return {'status': 'ok'}
