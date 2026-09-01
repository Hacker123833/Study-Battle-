# StudyBattle — Professional PDF Edition

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
4. No OpenAI API key is required for the local PDF/MCQ pipeline.
5. After deploy, open `/api/pdf_diagnostics`; `tesseract_available` should be `true`.

## Important
The free Render filesystem is not a permanent database. `studybattle_progress.json` and `uploaded_questions.json` persist only as long as the service filesystem persists. For production-scale persistence, replace these JSON files with Postgres/object storage.
