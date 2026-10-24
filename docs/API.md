# API reference

This document describes the current Flask API in `app.py` and lesson schema in `scraper/models.py`. Update it in the same change as any API contract change (see `AGENTS.md`).

Production base URL: `https://japanese-scraper.onrender.com`. Render Free may need time to wake after inactivity. Local examples below use `http://localhost:5000`; substitute the production base URL for hosted requests.

All endpoints are read-only and require no authentication. Successful API responses use `application/json`. Errors currently use Flask's default HTML error responses, including on `/api/` routes. No API endpoint starts ingestion or accepts an Ollama key.

## List articles

`GET /api/articles`

| Query parameter | Default | Behavior |
| --- | --- | --- |
| `page` | `1` | Integer page number, starting at 1. Each page contains at most 10 articles. |
| `status` | `ready` | One of `ready`, `pending`, `error`, or `all`. |
| `q` | empty string | Trimmed, case-insensitive substring search across the article title and the stored lesson's Python string representation, including its field names. |

Filters are applied before pagination. Article order follows the stored archive; ingestion sorts it by publication date and ID, newest first. An empty result has `total: 0`, `pages: 1`, and `articles: []`.

Example request:

```sh
curl 'http://localhost:5000/api/articles?page=1&status=ready&q=努力'
```

Response fields:

| Field | Type | Meaning |
| --- | --- | --- |
| `articles` | array of articles | Records on this page; schema below. |
| `page` | integer | Current page. |
| `pages` | integer | Total filtered pages, at least 1. |
| `total` | integer | Number of filtered articles. |
| `q` | string | Trimmed search query. |
| `status` | string | Selected status filter. |
| `coverage` | object | Discovery metadata; schema below. Empty before discovery. |
| `ready` | integer | Transcribed articles across the entire archive, independent of filters. |
| `discovered` | integer | All stored articles, independent of filters. |

Errors: `400` for an invalid status or a page that cannot be parsed as an integer; `404` for an integer page outside `1..pages`.

## Get an article

`GET /api/articles/<article_id>`

Returns one article object, irrespective of its transcription status. Use the opaque `id` returned by the list endpoint, including for legacy articles. Unknown IDs return `404`.

### Article object

| Field | Type | Availability / meaning |
| --- | --- | --- |
| `id` | string | Publisher article ID. |
| `url` | string | Canonical original article URL. |
| `date` | string | Publication date as `YYYY-MM-DD`, converted to Asia/Seoul. |
| `title` | string | Original article title. |
| `status` | string | `pending`, `ready`, or `error`. |
| `attempts` | integer | Present after a transcription attempt. |
| `images` | array of strings | Original body-image URLs, present after successful image discovery, even if subsequent transcription fails. |
| `lesson` | object | Present after successful, validated transcription. |
| `model` | string | Model name used for successful transcription. |
| `processed_at` | string | Successful transcription timestamp in ISO 8601 with Seoul UTC offset. |
| `error` | string | Exception class from a failed attempt, without raw error details. Removed after success. |

### Lesson object

| Field | Type | Meaning |
| --- | --- | --- |
| `expressions` | array of expression objects | At least one expression. |
| `notes` | array of strings | Additional transcribed notes; defaults to `[]`. |
| `uncertain_text` | array of strings | Illegible or uncertain text flagged by the model; defaults to `[]`. |

Each expression has a nonempty `japanese` string, plus `reading`, `translation`, and `explanation` strings (default `""`), and an `examples` array (default `[]`). Each example has a required `japanese` string and optional `reading` and `translation` strings (default `""`). Translations and explanations preserve Korean source text. Empty optional fields indicate missing text, not a guaranteed translation. Model transcription is not guaranteed accurate.

Illustrative lesson shape (not an actual article response):

```json
{
  "expressions": [
    {
      "japanese": "並々ならぬ努力",
      "reading": "なみなみならぬどりょく",
      "translation": "보통이 아닌 노력, 엄청난 노력",
      "explanation": "",
      "examples": []
    }
  ],
  "notes": [],
  "uncertain_text": []
}
```

### Coverage object

After discovery, `coverage` contains `discovered_at` (ISO 8601 timestamp with Seoul offset), `first_date` and `latest_date` (publication dates in the stored archive, or `null` if empty), and `feed_count` (integer count of eligible entries yielded by that discovery). Discovery coverage does not imply that every image has been transcribed.

## Health

`GET /health`

Returns `200` with `{"status": "ok"}`. This checks Flask availability; it does not test upstream services, model credentials, or archive completeness.

## Furigana display

HTML lesson titles, expressions, and Japanese example sentences render supplied readings as semantic `<ruby>` annotations above kanji runs only. Kana and punctuation are not annotated. Consecutive kanji use word-level readings rather than guessed character-by-character pronunciation. Missing, inconsistent, or ambiguous readings leave the source text unannotated. API responses continue to provide the original plain `japanese` and full `reading` strings; no HTML is added to JSON fields.

## HTML pages

- `GET /`: renders the article list with the same query parameters, defaults, filtering, pagination, and validation as `/api/articles`.
- `GET /articles/<article_id>`: renders an article's lesson or transcription status; unknown IDs return `404`.

Unsupported methods on these routes return `405`. Flask also supplies standard automatic `HEAD` and `OPTIONS` handling for the GET routes.
