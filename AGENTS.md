# Project conventions

- Stack: Flask, Jinja templates, Python 3.12+. No model API calls; ingestion is discovery-only.
- Use `.venv/bin/python` and `.venv/bin/pip`; dependencies are pinned in requirements.txt.
- Keep keys in ignored `.env` locally and GitHub Actions secrets remotely. Never print keys, model request headers, or raw exception bodies.
- Scrape only the Japanese section feed. Exhaust pagination for historical discovery; never fabricate URLs or guess missing dates. Convert publication timestamps to Asia/Seoul.
- Extract full article-body images, never cropped social thumbnails. Keep source URLs and model provenance.
- Validate transcription with Pydantic. Preserve Japanese/Korean text and explicit uncertainty; never fill illegible text with invented content.
- The read-only Flask app serves repository JSON, with exactly 10 articles per page. Do not add public scraping endpoints.
- Keep `docs/API.md` synchronized in the same change whenever routes, HTTP methods, parameters, defaults, validation, status codes, response fields, lesson schemas, authentication, or other externally observable API behavior changes. Update examples as well as descriptions. Before every handoff, check whether the change affects the API contract; if it does, update the API document before considering the work complete. For changes without API impact, verify that the existing document remains accurate; do not make cosmetic documentation edits just to touch the file.
- Discovery does not complete transcription. Keep new articles pending; preserve existing lessons and model provenance. Do not add model API calls without explicit authorization.
- Persist progress atomically after every article. Failed articles must remain retryable. Never mark archive transcription complete based on discovery alone.
- Mirror validated ready lessons into Firestore project `jlpt-practice-20a4e`, collection `japanese_lessons`, using publisher IDs. Keep existing JLPT collections untouched. Use keyless GitHub Workload Identity; never commit credential files. Never delete Firebase lessons during sync.
- Render Free serves the app; GitHub Actions owns daily 01:00 Asia/Seoul ingestion and commits durable JSON. Do not add an in-process scheduler to sleeping Free instances.
- Before handoff run `.venv/bin/python -m pytest`. Use mocks for normal tests; live model calls are explicit smoke checks.
- After making changes, run the required checks, commit the task's changes with a descriptive message, and push to the deployment branch so Render automatically redeploys. Verify that deployment succeeds and `/health` responds successfully before handoff. Proceed without asking for confirmation unless the user explicitly asks to keep changes local. Never include secrets or unrelated changes in the commit; report any blocked push or deployment accurately.
