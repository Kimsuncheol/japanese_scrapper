from scraper.furigana import furigana


def test_kanji_only_and_okurigana():
    result = str(furigana('彼女、怪我から見事に復帰しましたね。', 'かのじょ、けがからみごとにふっきしましたね。'))
    for base, reading in [('彼女','かのじょ'),('怪我','けが'),('見事','みごと'),('復帰','ふっき')]:
        assert f'<ruby>{base}<rp>(</rp><rt>{reading}</rt>' in result
    assert result.count('<ruby>') == 4
    assert 'しましたね。' in result
    assert '<ruby>から' not in result


def test_speaker_and_iteration_mark():
    result = str(furigana('B 並々ならぬ努力です。', 'なみなみならぬどりょくです。'))
    assert result.startswith('B <ruby>並々')
    assert '<rt>なみなみ</rt>' in result
    assert '<rt>どりょく</rt>' in result
    assert 'ならぬ<ruby>' in result


def test_no_guesses_or_markup_injection():
    assert str(furigana('こんにちは', 'こんにちは')) == 'こんにちは'
    assert str(furigana('日本語', '')) == '日本語'
    assert str(furigana('食べる', 'のむ')) == '食べる'
    assert str(furigana('<script>食べる</script>', 'たべる')) == '&lt;script&gt;食べる&lt;/script&gt;'
    assert '&lt;' in str(furigana('食べる<', 'たべる'))


def test_ambiguous_kana_anchor_is_not_guessed():
    assert str(furigana('漢あ字', 'かああじ')) == '漢あ字'



def test_html_uses_ruby_but_api_keeps_plain_text(tmp_path, monkeypatch):
    from app import app
    from scraper import storage
    monkeypatch.setenv('DATA_PATH', str(tmp_path / 'articles.json'))
    expression = {'japanese':'食べる','reading':'たべる','translation':'먹다', 'explanation':'',
                  'examples':[{'japanese':'私が食べる。','reading':'わたしがたべる。','translation':'내가 먹다.'}]}
    storage.write({'coverage':{},'articles':[{'id':'ruby','date':'2026-10-23','title':'lesson',
                  'url':'https://www.chosun.com/article','status':'ready','images':[],
                  'lesson':{'expressions':[expression], 'notes':[], 'uncertain_text':[]}}]})
    client = app.test_client()
    for path in ['/', '/articles/ruby']:
        html = client.get(path).get_data(as_text=True)
        assert '<ruby>食<rp>(</rp><rt>た</rt>' in html
        assert 'class="reading"' not in html
    html = client.get('/articles/ruby').get_data(as_text=True)
    assert '<ruby>私<rp>(</rp><rt>わたし</rt>' in html
    assert client.get('/api/articles/ruby').json['lesson']['expressions'][0] == expression
