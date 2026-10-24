# Project conventions

- Stack: Flask, Jinja templates, Python 3.12+, LangChain ChatOllama.
- Use `.venv/bin/python` and `.venv/bin/pip`; dependencies are pinned in requirements.txt.
- Keep keys in ignored `.env` locally and GitHub Actions secrets remotely. Never print keys, model request headers, or raw exception bodies.
- Scrape only the Japanese section feed. Exhaust pagination for historical discovery; never fabricate URLs or guess missing dates. Convert publication timestamps to Asia/Seoul.
- Extract full article-body images, never cropped social thumbnails. Keep source URLs and model provenance.
- Validate transcription with Pydantic. Preserve Japanese/Korean text and explicit uncertainty; never fill illegible text with invented content.
- The read-only Flask app serves repository JSON, with exactly 10 articles per page. Do not add public scraping endpoints.
- Keep `docs/API.md` synchronized in the same change whenever routes, HTTP methods, parameters, defaults, validation, status codes, response fields, lesson schemas, authentication, or other externally observable API behavior changes. Update examples as well as descriptions. Before every handoff, check whether the change affects the API contract; if it does, update the API document before considering the work complete. For changes without API impact, verify that the existing document remains accurate; do not make cosmetic documentation edits just to touch the file.
- Persist progress atomically after every article. Failed articles must remain retryable. Never mark archive transcription complete based on discovery alone.
- Render Free serves the app; GitHub Actions owns daily 01:00 Asia/Seoul ingestion and commits durable JSON. Do not add an in-process scheduler to sleeping Free instances.
- Before handoff run `.venv/bin/python -m pytest`. Use mocks for normal tests; live model calls are explicit smoke checks.
