# Kotoba — Japanese lesson archive

Flask serves existing validated lessons with a searchable Japanese/Korean study website and JSON API. Ten articles per page. The web app is read-only; keys and ingestion run outside browser requests.

## Local setup

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
.venv/bin/python -m scraper.cli --discover-only
.venv/bin/flask --app app run --port 5000
```

If `.env` already exists, preserve it. No model credentials are required.

## Historical coverage and URL analysis

The live public Japanese-section feed reported **5,878** articles on October 24, 2026, spanning **2003-11-11 through 2026-10-23** in Asia/Seoul. October 24 is a Saturday: the latest available lesson was Friday's. These are the earliest/latest entries found in the current feed, not proof that no earlier print lessons exist.

Two observed URL families:

- Modern: `https://www.chosun.com/national/nie/japanese/YYYY/MM/DD/ARTICLE_ID/`. IDs are opaque, typically 26 uppercase letters/digits; they cannot be generated from dates.
- Legacy: `https://www.chosun.com/site/data/html_dir/YYYY/MM/DD/NUMERIC_ID.html`. Section membership comes from the feed, not the path.

Discover through `/pf/api/v3/content/fetch/story-feed` with the section filter `/national/nie/japanese`, `size=100`, and the returned `next` offset. This public site endpoint is undocumented and may change. The scraper exhausts pagination on each discovery, rejects repeated pages or premature termination, deduplicates canonical URLs, and excludes future publication dates. Publication timestamps are converted to Asia/Seoul before date filtering.

Read the article's embedded `Fusion.globalContent` JSON and extract `content_elements` images. This avoids cropped promo/social thumbnails. Modern and earliest legacy image discovery were verified live. Existing records retain their source images and transcription provenance.

## Discovery without transcription

Ollama and LangChain have been removed. The CLI and daily workflow only discover articles; they make no model API calls. Run `.venv/bin/python -m scraper.cli` (or `--discover-only`) to exhaust the Japanese section feed and atomically save the archive.

Existing lessons and their original model provenance remain in `data/articles.json`. Newly discovered articles remain `pending`; existing failures remain available for future retry with a separately authorized transcription method. Discovery never marks transcription complete. The former transcription options and automatic backfill continuation have been removed.

Lesson validation still uses Pydantic for Firebase synchronization. No replacement paid model is configured.

## Render Free deployment

The included `render.yaml` configures a **Free** Flask web service. It serves versioned JSON; no model key is needed on Render.

1. Create a GitHub repository and push this project, including `data/articles.json`. Never commit `.env`.
2. Enable Actions and run **Daily Japanese lessons** to discover articles and synchronize existing validated lessons to Firebase. No model secrets are used.
3. In Render, choose **New → Blueprint**, connect that repository and apply `render.yaml`. Confirm the plan is Free. Enable automatic deployment on commits so each data update reaches the website.
4. Open `/health`, `/`, and `/api/articles` to verify the deployment.

The workflow requests ingestion daily at **01:00 Asia/Seoul**, which is **16:00 UTC the previous day**. GitHub Actions schedules are best-effort and can be delayed. Scheduled workflows run on the default branch; GitHub may disable inactive public-repository schedules after 60 days. Free runner availability depends on your GitHub plan and usage.

Render Free sleeps after inactivity, loses filesystem changes on restart/redeploy, and provides no free persistent disk or free cron service. Therefore an in-process Flask scheduler cannot reliably meet this requirement. The external workflow commits its results to GitHub; Render redeploys them. A cold Render service can take time to respond. This architecture has no strict exactly-01:00 guarantee.

The project is deployed at **https://japanese-scraper.onrender.com** on Render Free in Singapore, serving the GitHub repository's `master` branch with automatic deployment on commits. The daily workflow performs discovery and Firebase synchronization only. Dashboard: https://dashboard.render.com/web/srv-dbea44i9lscs73af1dpg .

## Lesson notes and glossary

The source image's glossary below the dashed horizontal separator belongs to the **Lesson notes** section, not the numbered main expressions. Validated lessons store these terms in `lesson.vocabulary`, with Japanese, reading, and Korean meaning. For compatibility with the Daily Japanese app, `lesson.notes` includes a plain-text copy of every glossary entry as well as existing free-form notes. The website excludes those copies when rendering structured vocabulary to avoid duplicates. Both are rendered together, with furigana above kanji in structured vocabulary entries.

Run `.venv/bin/python -m scraper.lesson_notes` to organize legacy records. It preserves the lead expression and entries with explanations/dialogue; other standalone entries move intact into vocabulary. No words, readings, translations, or existing notes are discarded. The daily workflow applies this before Firebase synchronization, including sync-only runs.

## Firebase lesson storage

Validated completed lessons are mirrored to Firebase project **JLPT practice (`jlpt-practice-20a4e`)**, Firestore collection **`japanese_lessons`**, with the publisher article ID as document ID. Sync metadata and archive status counts live at **`japanese_scraper/archive`**. Existing JLPT collections are untouched. The Flask site continues serving its versioned JSON snapshot to keep Render requests inexpensive.

```sh
# Uses local Google Application Default Credentials:
.venv/bin/python -m scraper.firebase_sync
```

The daily ingestion workflow authenticates with Google Workload Identity Federation (repository and `master` branch restricted), then synchronizes existing completed lessons after discovery. No service-account private key is used or required on Render. Changed records are written in bounded batches; matching hashes skip duplicate writes. Failed syncs fail the workflow, preserving the JSON archive for retry. Firestore failures do not mark a lesson transcription as failed. Rerunning sync resumes safely from already committed records. Do not run concurrent sync writers.

To verify or retry just Firebase synchronization in GitHub Actions, manually run **Daily Japanese lessons** with **sync_only** selected. This skips discovery; no workflow mode calls a model API.

Firestore's existing security rules are preserved; access from another JLPT client is still subject to that client's existing permissions. See [API documentation](docs/API.md) for the persisted document schema.

## API and checks

Open [/docs](https://japanese-scraper.onrender.com/docs) for the HTML documentation, generated directly from `docs/API.md`. See [the API reference](docs/API.md) for parameters, response schemas, and errors. Codex must keep this reference synchronized with API changes, as required by `AGENTS.md`.

- `GET /api/articles?page=1&status=ready&q=...` — ten records per page; status also accepts `all`, `pending`, or `error`.
- `GET /api/articles/<id>` — source, provenance, images and structured lesson.
- `GET /health` — health check.

```sh
.venv/bin/python -m pytest -q
```

Tests mock upstream requests and verify archive pagination, Korean dates, full image selection, schema rejection, filtering, HTML escaping and page boundaries. Normal tests make no live upstream calls.

## References

- Chosun section: https://www.chosun.com/national/nie/japanese/
- Example: https://www.chosun.com/national/nie/japanese/2026/10/20/DABOV5NZCVFBFLI2SOGJQYMVRA/
- Render Free limitations: https://render.com/docs/free
- Scheduled-workflow limitations: https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule
