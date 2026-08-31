# StudyBattle Web

A deployable Flask web version based directly on the uploaded StudyBattle V7 code.

## Included
- Login and account creation
- Saved XP, wins, battles, accuracy, streak, coins and levels
- Subject/topic selection
- Classic, Sudden Death, Streak Master and Tournament modes
- 5/10/15/20/30 question battles
- Multiplayer rooms up to 15 players
- Live ranking and room chat
- Tournament surprises and cumulative standings
- Battle awards, Hall of Fame and dare roulette
- Mobile-friendly single-page UI
- Persistent username restoration in the browser

## Run locally
```bash
python -m pip install -r requirements.txt
python app.py
```
Then open `http://127.0.0.1:5000`.

## Deploy on Render
1. Create a GitHub repository and upload these files.
2. In Render, create a new Web Service from the repository.
3. Render can use the included `render.yaml`, or use:
   - Build: `pip install -r requirements.txt`
   - Start: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 8 --timeout 120`

## Important production note
The current V7 code stores progress in `studybattle_progress.json`. That is suitable for local testing but is not durable on many cloud hosts. For a public production deployment, move accounts/progress/rooms to a persistent database (SQLite/PostgreSQL) and use a shared realtime backend for multiplayer scaling.
