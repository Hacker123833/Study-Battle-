# StudyBattle — Professional PDF Edition (VNext 2)

A Flask multiplayer study-battle app with local PDF extraction/OCR and grounded MCQ generation.

## Included upgrades
- Clean professional responsive UI with mobile-first cards, better spacing, states and buttons
- PDF study-set builder up to 100 MB / 300 pages
- Text PDFs and scanned/image PDFs via PyMuPDF + Tesseract OCR
- Docker build verifies `tesseract` and `pdftoppm` are installed
- `/api/pdf_diagnostics` endpoint for deployment troubleshooting
- No pre-installed question bank; questions come from uploaded study sets
- Study-set catalog with owner-only delete controls
- Drag-and-drop PDF upload
- Duplicate-question protection
- Classic, Sudden Death, Streak Master and Tournament modes
- Multiplayer rooms, live ranking, chat, achievements, XP, coins and tournament rewards
- Persistent progress JSON storage

## Render
1. Push/upload this project to GitHub.
2. Create a Render Web Service from the repository.
3. Keep Runtime = Docker. Render will use the root `Dockerfile`.
4. No API key is required for the app to run at all — a local PDF/MCQ pipeline works out of the box.
5. **Recommended:** add an environment variable `ANTHROPIC_API_KEY` with your own Anthropic API key to switch question generation to the LLM-quality engine (see below).
6. After deploy, open `/api/pdf_diagnostics`; `tesseract_available` should be `true`, and `ai_generation_enabled` will tell you whether the AI generator is active.

## AI-powered question generation (new)
Set these environment variables on your host (Render → your service → Environment):
- `ANTHROPIC_API_KEY` — your Anthropic API key. Get one at https://console.anthropic.com. **Required** to enable the LLM generator; without it the app silently uses the local generator, so it keeps working either way.
- `ANTHROPIC_MODEL` (optional) — defaults to `claude-sonnet-5`.

When a key is present, every PDF upload is turned into MCQs by an LLM prompted to:
- Stay strictly grounded in the extracted PDF text (no invented facts).
- Vary question types (definitions, cause/effect, comparisons, applied scenarios, numeric recall, true/false-style).
- Write plausible, non-generic distractors instead of "all/none of the above".
- Include a short explanation and the source page for every question.
- Cover the *whole* document (chunks are sampled evenly across all pages, not just the start) even on long PDFs.

If the API call fails or only partially succeeds (rate limit, network blip, thin source text), the app automatically tops up the remainder with the local generator so you always get the number of questions you asked for — generation never hard-fails.

## PDF extraction accuracy
- Native text extraction (PyMuPDF block-based) is tried first on every page; OCR only kicks in for genuinely near-empty/scanned pages, so text PDFs stay fast.
- OCR now renders pages at 2.0x scale (up from 1.5x) for sharper glyph recognition, with an automatic PSM 3 → PSM 6 fallback pass on pages that come back mostly blank.
- Hyphenated line-wraps ("mag-\nnetic") are repaired, repeated headers/footers are stripped without deleting real repeated content, and there's a `pypdf` fallback if PyMuPDF extraction comes back too thin.
- Tune OCR speed/accuracy with the optional `OCR_RENDER_SCALE` environment variable (default `2.0`; try `2.5` for very small/dense scans, or `1.5` if you need faster processing on large scanned decks).

## Important
The free Render filesystem is not a permanent database. `studybattle_progress.json` and `uploaded_questions.json` persist only as long as the service filesystem persists. For production-scale persistence, replace these JSON files with Postgres/object storage.


## PDF Engine (VNext)

- Asynchronous PDF processing: the browser no longer waits on a long upload request.
- Live progress percentage, current stage, page progress and estimated remaining time.
- Native PDF text extraction first; OCR is used only for scanned/image pages.
- PyMuPDF + pypdf fallback extraction.
- Page-aware source chunks for study-set generation.
- Source-grounded MCQ generation with duplicate filtering and distractor quality checks.
- No OpenAI/API key is required for the local generator.
- Docker installs Tesseract OCR and Poppler automatically.

### Expected processing time
Text PDFs are usually fast. Scanned PDFs can take substantially longer because each image page must be OCRed; the UI now shows the live estimate instead of appearing frozen.


## VNext UI
Includes a polished Home/Practice/You navigation, solo source-grounded Practice mode, and the existing multiplayer arena.


## VNext 2 upgrades
- User-selectable PDF generation count: 10/20/30/50/75/100/150/200 MCQs.
- Background processing with stage-aware live progress and server-calculated ETA.
- Faster selective OCR: OCR only near-empty/image pages; 1.5x rendering for better free-tier speed.
- Page-aware extraction using PyMuPDF blocks, line-wrap repair, repeated header/footer removal and pypdf fallback.
- Stronger duplicate filtering across the entire uploaded question library.
- More diverse source-grounded question families with explanations and source-page provenance.
- Generator refuses to invent unsupported facts when the PDF does not contain enough reliable material.
- Cleaner PDF builder controls and progress details on mobile.
