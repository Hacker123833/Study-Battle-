# StudyBattle — Smart Study Battles

A mobile-friendly Flask multiplayer study quiz. Study sets are created from uploaded PDFs; there is **no pre-installed question bank**.

## Main features
- PDF upload with text extraction and OCR fallback for scanned pages
- Content-based MCQ generation without an external AI/API key
- Duplicate-question filtering
- User-created study sets with question counts
- Delete your own study sets from the Arena
- Classic, Sudden Death, Streak Master and Tournament modes
- Multiplayer rooms, live ranking, chat, XP, coins, achievements and profile
- Render-ready Gunicorn configuration

## Deploy on Render
This project includes `render.yaml`, `Procfile`, `Dockerfile` and `requirements.txt`.

For a Render Web Service using the Python build, use:

**Build command**
```bash
pip install -r requirements.txt
```

**Start command**
```bash
gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 8 --timeout 180
```

## Important
The current app stores account progress and uploaded questions in local JSON files. This is suitable for testing/small deployments, but a production-scale version should use PostgreSQL or another persistent database/storage service.


## PDF processing fix
This build uses Docker so the server includes the Tesseract OCR system package required for scanned/image PDFs. The local MCQ generator also uses a set for duplicate tracking, fixing the `list` object has no attribute `add` upload error.
