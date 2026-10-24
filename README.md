# Kotoba — Japanese lesson archive

Flask + LangChain + Ollama image transcription, with a searchable Japanese/Korean study website and JSON API. Ten articles per page. The web app is read-only; keys and ingestion run outside browser requests.

## Local setup

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
# Set OLLAMA_API_KEY in .env (an ignored file).
.venv/bin/python -m scraper.cli --discover-only
.venv/bin/python -m scraper.cli --limit 10
.venv/bin/flask --app app run --port 5000
```

If `.env` already exists, preserve it. Default cloud model: `gemma4:31b`. For local Ollama, set `OLLAMA_BASE_URL=http://localhost:11434`, select an installed vision model, and leave the key empty. Render Free cannot host the model itself.

## Historical coverage and URL analysis

The live public Japanese-section feed reported **5,878** articles on October 24, 2026, spanning **2003-11-11 through 2026-10-23** in Asia/Seoul. October 24 is a Saturday: the latest available lesson was Friday's. These are the earliest/latest entries found in the current feed, not proof that no earlier print lessons exist.

Two observed URL families:

- Modern: `https://www.chosun.com/national/nie/japanese/YYYY/MM/DD/ARTICLE_ID/`. IDs are opaque, typically 26 uppercase letters/digits; they cannot be generated from dates.
- Legacy: `https://www.chosun.com/site/data/html_dir/YYYY/MM/DD/NUMERIC_ID.html`. Section membership comes from the feed, not the path.

Discover through `/pf/api/v3/content/fetch/story-feed` with the section filter `/national/nie/japanese`, `size=100`, and the returned `next` offset. This public site endpoint is undocumented and may change. The scraper exhausts pagination on each discovery, rejects repeated pages or premature termination, deduplicates canonical URLs, and excludes future publication dates. Publication timestamps are converted to Asia/Seoul before date filtering.

Read the article's embedded `Fusion.globalContent` JSON and extract `content_elements` images. This avoids cropped promo/social thumbnails. Modern and earliest legacy image discovery were verified live. Multiple body images are sent together to the model.

## OCR and backfill

```sh
# Index every published article without using the model:
.venv/bin/python -m scraper.cli --discover-only
# Process ten articles manually, newest first:
.venv/bin/python -m scraper.cli --limit 10
# Process the complete remaining historical backlog (long, uses model quota):
.venv/bin/python -m scraper.cli --limit 0
# Target an indexed article:
.venv/bin/python -m scraper.cli --url 'https://www.chosun.com/national/nie/japanese/2026/10/20/DABOV5NZCVFBFLI2SOGJQYMVRA/'
```

Discovery and transcription are separate: indexed articles remain `pending` until their images produce valid lesson JSON. Failures become `error` and are retried in later batches. Successful articles are skipped. Progress is written atomically after each article. Run one writer at a time; GitHub Actions serializes runs. A full initial backfill requires processing all pending articles; the daily workflow now defaults to the full backlog. It processes three articles concurrently for about 20 minutes, commits progress, and dispatches a continuation while progress is being made. Authentication/quota failures stop continuation; a run with no successful transcriptions also stops to prevent endless retries. Check workflow logs and rerun after resolving the failure. Manual CLI calls still default to ten articles.

Cloud Ollama currently does not support enforced JSON-schema outputs. We prompt for JSON and validate using Pydantic with three attempts. The schema separates Japanese expressions, readings, Korean meanings, explanations, dialogue examples, notes, and uncertain text. OCR accuracy still requires checking the source image. Missing optional text stays empty; no guessed translation is required. Each successful record stores the model, original image URLs, article URL, and processing timestamp.

Data lives in `data/articles.json`. It includes archive metadata plus per-article transcription state. Source images remain at their publisher URLs; they are downloaded into memory for OCR. Failed upstream image URLs remain visible as failures rather than invented lessons.

## Render Free deployment

The included `render.yaml` configures a **Free** Flask web service. It serves versioned JSON; no Ollama key is needed on Render.

1. Create a GitHub repository and push this project, including `data/articles.json`. Never commit `.env`.
2. Add the key as the GitHub Actions repository secret **OLLAMA_API_KEY**. Optionally set repository variable **OLLAMA_MODEL**.
3. Enable Actions and run **Daily Japanese lessons** manually for the initial backfill (the default is now `0`). The `limit` input accepts `0` for all remaining articles; jobs save progress after approximately 20 minutes and automatically continue full-archive runs; each job has a 40-minute safety cap. Retain the JSON progress commit even when individual articles fail.
4. In Render, choose **New → Blueprint**, connect that repository and apply `render.yaml`. Confirm the plan is Free. Enable automatic deployment on commits so each data update reaches the website.
5. Open `/health`, `/`, and `/api/articles` to verify the deployment.

The workflow requests ingestion daily at **01:00 Asia/Seoul**, which is **16:00 UTC the previous day**. GitHub Actions schedules are best-effort and can be delayed. Scheduled workflows run on the default branch; GitHub may disable inactive public-repository schedules after 60 days. Free runner availability depends on your GitHub plan and usage. Ollama cloud quota/pricing is independent of Render Free.

Render Free sleeps after inactivity, loses filesystem changes on restart/redeploy, and provides no free persistent disk or free cron service. Therefore an in-process Flask scheduler cannot reliably meet this requirement. The external workflow commits its results to GitHub; Render redeploys them. A cold Render service can take time to respond. This architecture has no strict exactly-01:00 guarantee.

The project is deployed at **https://japanese-scraper.onrender.com** on Render Free in Singapore, serving the GitHub repository's `master` branch with automatic deployment on commits. The GitHub Actions `OLLAMA_API_KEY` secret is configured, and the daily workflow is active. Dashboard: https://dashboard.render.com/web/srv-dbea44i9lscs73af1dpg .

## API and checks

See [the API reference](docs/API.md) for parameters, response schemas, and errors. Codex must keep this reference synchronized with API changes, as required by `AGENTS.md`.

- `GET /api/articles?page=1&status=ready&q=...` — ten records per page; status also accepts `all`, `pending`, or `error`.
- `GET /api/articles/<id>` — source, provenance, images and structured lesson.
- `GET /health` — health check.

```sh
.venv/bin/python -m pytest -q
```

Tests mock upstream requests and verify archive pagination, Korean dates, full image selection, schema rejection, filtering, HTML escaping and page boundaries. Live image extraction/model smoke checks are separate from tests.

## References

- Chosun section: https://www.chosun.com/national/nie/japanese/
- Example: https://www.chosun.com/national/nie/japanese/2026/10/20/DABOV5NZCVFBFLI2SOGJQYMVRA/
- Ollama cloud: https://docs.ollama.com/cloud
- Ollama structured-output limitation: https://docs.ollama.com/capabilities/structured-outputs
- LangChain integration: https://docs.langchain.com/oss/python/integrations/chat/ollama
- Render Free limitations: https://render.com/docs/free
- Scheduled-workflow limitations: https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule
