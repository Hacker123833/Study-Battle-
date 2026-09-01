
# ULTIMATE MULTIPLAYER FEATURES
MAX_PLAYERS = 15
QUESTION_COUNTS = [5, 10, 15, 20, 30, 50, 75, 100, 150, 200]
PDF_QUESTION_COUNTS = [10, 20, 30, 50, 75, 100, 150, 200]
ULTIMATE_FEATURES = {
    "host_controls": True,
    "live_leaderboard": True,
    "chat_reactions": True,
    "team_battles": True,
    "boss_battle": True,
    "battle_statistics": True,
    "rematch": True,
    "achievements": True,
    "daily_missions": True,
    "mvp_titles": True,
    "champion_crown": True,
    "win_streak_rewards": True,
    "battle_coins": True,
    "player_levels": True,
    "hall_of_fame": True,
    "winner_choice": True,
}

from flask import Flask, request, jsonify, render_template_string
import random, string, threading, time, json, os, hashlib, secrets, re, copy, io, unicodedata, difflib, shutil, math, statistics
from werkzeug.utils import secure_filename

try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None

try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None

try:
    import pytesseract
    from PIL import Image
    _tesseract_path = shutil.which("tesseract")
    if _tesseract_path:
        pytesseract.pytesseract.tesseract_cmd = _tesseract_path
except Exception:
    pytesseract = None
    Image = None
    _tesseract_path = None

import urllib.request, urllib.error

# ---- AI question generation (optional, uses your own Anthropic API key) ----
# Set ANTHROPIC_API_KEY as an environment variable on your host (Render, Docker, etc.)
# to unlock high-quality LLM-generated MCQs. Without a key the app automatically
# falls back to the local source-grounded generator below, so it always works.
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5").strip()
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
AI_GENERATION_ENABLED = bool(ANTHROPIC_API_KEY)
# 2.0x render scale = noticeably sharper OCR than the old 1.5x, at a modest speed cost.
OCR_RENDER_SCALE = float(os.environ.get("OCR_RENDER_SCALE", "2.0"))

app = Flask(__name__)
PORT = int(os.environ.get("PORT", 5000))
SAVE_FILE = "studybattle_progress.json"
CUSTOM_QUESTIONS_FILE = "uploaded_questions.json"
MAX_PDF_BYTES = 100 * 1024 * 1024
MAX_PDF_PAGES = 300
uploaded_questions = []
upload_lock = threading.Lock()
pdf_jobs = {}
pdf_jobs_lock = threading.Lock()
PDF_JOB_TTL = 60 * 60

MAX_PLAYERS = 15
MIN_PLAYERS = 2
QUESTION_TIME = 15
BASE_POINTS = 5
lock = threading.Lock()
rooms = {}

# Strong topic-based question randomization: questions are dealt from a shuffled
# deck and are not repeated until the available pool for that selection is exhausted.
QUESTION_DECKS = {}
QUESTION_DECK_LOCK = threading.Lock()

# Testing accounts are kept in the database but never shown on Hall of Fame.
HALL_OF_FAME_HIDDEN_NAMES = {"test", "test 1", "test1", "jordan"}
players = {}

DARE_LIST = [
    'Do your funniest walk for 20 seconds.', 'Pretend you are a news reporter for 30 seconds.', 
    'Speak like a robot for 30 seconds.', 'Do 5 funny poses.', 'Pretend to be a teacher for 30 seconds.', 
    'Give a dramatic speech about why you lost.', 'Act like a chicken for 20 seconds.', 
    'Make your funniest serious face.', 'Do a victory dance even though you came last.', 
    'Introduce yourself like a celebrity.', 'Say three tongue twisters.', 'Pretend to be a sports commentator.', 
    'Walk like a penguin for 20 seconds.', 'Make up a funny slogan for StudyBattle.', 
    'Pretend to answer an imaginary phone call.', 'Do your best superhero pose.', 
    'Give everyone a dramatic thumbs-up.', 'Pretend you just won a million rupees.', 
    'Act like a confused tourist for 20 seconds.', 'Pretend you are presenting breaking news.', 
    'Say your name in three different funny voices.', 'Pretend to be an NPC for 30 seconds.', 
    'Give a dramatic explanation of why your score is low.', 'Do a slow-motion celebration.', 
    'Pretend you are a game-show host.', 'Make up a two-line funny poem.', 
    'Pretend you are stuck in an invisible box.', 'Do your best statue impression.', 
    'Say a sentence like a movie villain.', 'Pretend you are giving a motivational speech.', 
    'Make a funny face for five seconds.', 'Pretend you are a football commentator.', 
    'Walk three steps like a cartoon character.', 'Pretend you are accepting an award.', 
    'Give yourself a ridiculous nickname.', "Say 'I will study harder' dramatically.", 
    'Pretend you are announcing a school assembly.', 'Do a tiny celebration dance.', 
    'Pretend you are an alien visiting Earth.', 'Describe your day like a documentary narrator.', 
    'Pretend you are selling an imaginary product.', 'Give a dramatic slow clap.', 
    'Pretend you are a weather reporter.', 'Say one sentence in an extremely dramatic voice.', 
    'Create a funny handshake with another player.', 'Pretend you are a very confused professor.', 
    'Do a 10-second invisible guitar solo.', 'Give a dramatic acceptance speech for coming last.', 
    'Pretend your pencil is a microphone and host a concert.', 'Pretend you are announcing the final score of a World Cup.'
]

# Built-in question bank intentionally removed. Study sets are created from uploaded PDFs.
def normalize_text(value):
    value = unicodedata.normalize("NFKC", str(value or "")).lower()
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", value)).strip()


def load_uploaded_questions():
    global uploaded_questions
    if not os.path.exists(CUSTOM_QUESTIONS_FILE):
        uploaded_questions = []
        return
    try:
        with open(CUSTOM_QUESTIONS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        uploaded_questions = data if isinstance(data, list) else []
    except Exception:
        uploaded_questions = []


def save_uploaded_questions():
    tmp = CUSTOM_QUESTIONS_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(uploaded_questions, f, ensure_ascii=False, indent=2)
    os.replace(tmp, CUSTOM_QUESTIONS_FILE)



def clean_pdf_text(text):
    """High-quality PDF text normalization while preserving scientific notation."""
    text = unicodedata.normalize("NFKC", text or "")
    text = text.replace("\x00", " ").replace("\r\n", "\n").replace("\r", "\n")
    # Repair common PDF line-wrap/hyphenation damage: "mag-\nnetic" -> "magnetic".
    text = re.sub(r"(?<=\w)-\n(?=\w)", "", text)
    # Join ordinary wrapped lines, but keep paragraph/list boundaries.
    text = re.sub(r"(?<![.!?:;])\n(?=[a-z0-9(])", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def _job_update(job_id, **changes):
    with pdf_jobs_lock:
        job = pdf_jobs.get(job_id)
        if not job:
            return
        job.update(changes)
        job["updated_at"] = time.time()

def _cleanup_pdf_jobs():
    cutoff = time.time() - PDF_JOB_TTL
    with pdf_jobs_lock:
        for jid in list(pdf_jobs):
            if pdf_jobs[jid].get("updated_at", 0) < cutoff:
                pdf_jobs.pop(jid, None)

def _page_native_text(page):
    try:
        # Blocks preserve a little more document structure than plain extraction.
        blocks = page.get_text("blocks") or []
        blocks = sorted(blocks, key=lambda b: (round(b[1], 1), round(b[0], 1)))
        pieces = []
        for b in blocks:
            if len(b) >= 5 and str(b[4] or "").strip():
                pieces.append(str(b[4]).strip())
        return clean_pdf_text("\n\n".join(pieces))
    except Exception:
        try:
            return clean_pdf_text(page.get_text("text") or "")
        except Exception:
            return ""

def _ocr_page(page):
    if pytesseract is None or Image is None or not _tesseract_path or fitz is None:
        return ""
    # Higher render scale = sharper glyphs = fewer OCR misreads.
    pix = page.get_pixmap(matrix=fitz.Matrix(OCR_RENDER_SCALE, OCR_RENDER_SCALE), alpha=False)
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    try:
        # PSM 3 (auto page segmentation) is best for normal pages; PSM 6 (uniform
        # block) sometimes rescues pages that PSM 3 reads as near-empty (e.g. dense
        # tables or single-column slides), so we try it as a fallback, not a default.
        text = pytesseract.image_to_string(img, lang="eng", config="--oem 3 --psm 3") or ""
        if len(re.sub(r"\s+", "", text)) < 40:
            alt = pytesseract.image_to_string(img, lang="eng", config="--oem 3 --psm 6") or ""
            if len(re.sub(r"\s+", "", alt)) > len(re.sub(r"\s+", "", text)):
                text = alt
        return clean_pdf_text(text)
    finally:
        img.close()

def _remove_repeated_marginal_text(pages):
    """Remove repeated headers/footers without deleting real repeated concepts."""
    if len(pages) < 4:
        return pages
    counts = {}
    for p in pages:
        lines = [re.sub(r"\s+", " ", x).strip() for x in p.get("text", "").splitlines()]
        for line in set(lines[:2] + lines[-2:]):
            n = normalize_text(line)
            if 3 <= len(n) <= 100:
                counts[n] = counts.get(n, 0) + 1
    threshold = max(4, int(len(pages) * 0.30))
    repeated = {k for k,v in counts.items() if v >= threshold}
    if not repeated:
        return pages
    for p in pages:
        lines = p.get("text", "").splitlines()
        cleaned=[]
        for line in lines:
            n=normalize_text(line)
            if n in repeated and len(n) < 100:
                continue
            cleaned.append(line)
        p["text"] = clean_pdf_text("\n".join(cleaned))
    return pages

def extract_pdf_text(file_bytes, job_id=None):
    """Notebook-style page-aware ingestion with native extraction + selective OCR."""
    _cleanup_pdf_jobs()
    if fitz is None:
        raise RuntimeError("PyMuPDF is not available on the server.")
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as e:
        raise ValueError("This file could not be opened as a valid PDF.") from e
    if doc.is_encrypted and not doc.authenticate(""):
        doc.close()
        raise ValueError("Password-protected PDFs are not supported unless they open without a password.")
    page_count=len(doc)
    if page_count==0:
        doc.close(); raise ValueError("The PDF has no pages.")
    if page_count>MAX_PDF_PAGES:
        doc.close(); raise ValueError(f"This PDF has {page_count} pages. The limit is {MAX_PDF_PAGES} pages.")

    pages=[]; ocr_pages=0; total_chars=0; started=time.time()
    try:
        for i,page in enumerate(doc):
            native=_page_native_text(page)
            compact=len(re.sub(r"\s+", "", native))
            # OCR only genuinely image-like/near-empty pages.
            used_ocr=False; text=native
            if compact < 100 and _tesseract_path:
                ocr=_ocr_page(page)
                if len(re.sub(r"\s+", "", ocr)) > max(compact*1.25, 80):
                    text=ocr; used_ocr=True; ocr_pages+=1
            text=clean_pdf_text(text)
            pages.append({"page":i+1,"text":text,"ocr":used_ocr,"chars":len(text)})
            total_chars += len(text)
            if job_id:
                elapsed=max(0.1,time.time()-started)
                done=i+1
                pct=5+int(done/page_count*62)
                per_page=elapsed/done
                remaining=max(0, page_count-done)*per_page
                _job_update(job_id, progress=pct, stage="extracting", current_page=done,
                            total_pages=page_count, ocr_pages=ocr_pages,
                            message=f"Reading page {done} of {page_count}" + (" • OCR" if used_ocr else ""),
                            eta_seconds=round(remaining))
    finally:
        doc.close()

    pages=_remove_repeated_marginal_text(pages)
    if job_id:
        _job_update(job_id, progress=69, stage="cleaning", message="Cleaning text, removing repeated headers and organizing pages…", eta_seconds=5)

    if total_chars < 80 and PdfReader is not None:
        try:
            reader=PdfReader(io.BytesIO(file_bytes), strict=False)
            fallback=[]
            for i,pg in enumerate(reader.pages[:MAX_PDF_PAGES]):
                txt=clean_pdf_text(pg.extract_text() or "")
                fallback.append({"page":i+1,"text":txt,"ocr":False,"chars":len(txt)})
            if sum(x["chars"] for x in fallback)>total_chars:
                pages=fallback; total_chars=sum(x["chars"] for x in pages)
        except Exception:
            pass
    return pages,page_count,ocr_pages

def build_study_chunks(pages, max_chars=2400):
    """Create small overlapping source chunks similar to an AI study notebook."""
    chunks = []
    for p in pages:
        text = clean_pdf_text(p.get("text", ""))
        if not text:
            continue
        paragraphs = [x.strip() for x in re.split(r"\n\s*\n", text) if x.strip()]
        current = ""
        for para in paragraphs:
            if len(current) + len(para) + 1 <= max_chars:
                current = (current + " " + para).strip()
            else:
                if current:
                    chunks.append({"page": p["page"], "text": current})
                current = para[:max_chars]
        if current:
            chunks.append({"page": p["page"], "text": current})
    return chunks



def _sentence_records(pages):
    records=[]
    for p in pages:
        text=clean_pdf_text(p.get("text", ""))
        if not text: continue
        # Preserve page provenance while splitting.
        for part in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9(])|\n{2,}|\n(?=[A-Z][^\n]{2,100}:)", text):
            part=re.sub(r"^[-–—•●▪◦\s]+", "", part).strip()
            part=re.sub(r"\s+", " ", part)
            if 25<=len(part)<=500 and len(re.findall(r"\b\w+\b",part))>=5:
                records.append({"text":part.rstrip("."),"page":p.get("page",0)})
    # Semantic-ish dedupe using token shingles + fuzzy similarity.
    unique=[]
    seen=set()
    for r in records:
        key=normalize_text(r["text"])
        if not key or key in seen: continue
        if any(len(key)>45 and len(normalize_text(x["text"]))>45 and difflib.SequenceMatcher(None,key,normalize_text(x["text"])).ratio()>=0.94 for x in unique[-250:]):
            continue
        seen.add(key); unique.append(r)
    return unique

def split_sentences(text):
    return [r["text"] for r in _sentence_records([{"page":0,"text":text}])]

def _extract_candidate_facts(pages):
    records=_sentence_records(pages)
    facts={"definitions":[],"formulas":[],"units":[],"terms":[],"relations":[],"numbers":[],"comparisons":[],"examples":[]}
    for r in records:
        sent=r["text"]; page=r["page"]
        # Definitions / meanings.
        m=re.match(r"^(?:The\s+)?(.{2,90}?)\s+(?:is|are|means|refers to|denotes|is defined as)\s+(.{10,280})$",sent,re.I)
        if m:
            term=_clean_term(m.group(1)); definition=m.group(2).strip(" .")
            if 1<=len(term.split())<=10:
                facts["definitions"].append((term,definition,page))
        # Formulas/equations.
        m=re.search(r"(?:formula|equation|relation)\s+(?:for\s+)?(.{2,90}?)\s*(?:is|:|=)\s*([A-Za-z0-9_()\[\]{}+\-*/^√≈≤≥·.= ]{2,160})$",sent,re.I)
        if m and any(ch in m.group(2) for ch in "=+-*/"):
            facts["formulas"].append((m.group(1).strip(" :,-"),m.group(2).strip(),page))
        # Units.
        m=re.search(r"(?:unit|SI\s+unit)\s+of\s+(.{2,100}?)\s+(?:is|are|=|equals)\s+(.{1,60})$",sent,re.I)
        if m: facts["units"].append((m.group(1).strip(" :,-"),m.group(2).strip(" ."),page))
        # Naming.
        m=re.search(r"(.{2,100}?)\s+(?:is|are)\s+(?:called|known as)\s+([A-Za-z][A-Za-z0-9()\- ]{1,70})$",sent,re.I)
        if m: facts["terms"].append((m.group(1).strip(" :,-"),m.group(2).strip(" ."),page))
        # Relationships and comparisons.
        if re.search(r"\b(directly proportional|inversely proportional|increases|decreases|depends on|because|therefore|caused by|due to|greater than|less than|higher than|lower than|whereas|while)\b",sent,re.I):
            facts["relations"].append((sent,page))
        if re.search(r"\b(for example|example|such as|e\.g\.)\b",sent,re.I):
            facts["examples"].append((sent,page))
        if re.search(r"\b(whereas|while|compared with|greater than|less than|higher than|lower than|more than|fewer than)\b",sent,re.I):
            facts["comparisons"].append((sent,page))
        if re.search(r"\d",sent): facts["numbers"].append((sent,page))
    # Deduplicate fact lists.
    for k,v in facts.items():
        out=[]; seen=set()
        for item in v:
            key=normalize_text(" ".join(map(str,item[:2])))
            if key not in seen: seen.add(key); out.append(item)
        facts[k]=out
    return facts,records

def _question_is_duplicate(question, existing):
    key=normalize_text(question)
    if not key: return True
    qtokens=set(key.split())
    for old in existing:
        old_key=normalize_text(old)
        if not old_key: continue
        if key==old_key: return True
        if len(key)>=35 and len(old_key)>=35:
            ratio=difflib.SequenceMatcher(None,key,old_key).ratio()
            if ratio>=0.86: return True
            ot=set(old_key.split())
            if len(qtokens)>=8 and len(ot)>=8 and len(qtokens&ot)/max(1,min(len(qtokens),len(ot)))>=0.88: return True
    return False

def _clean_term(term):
    term=re.sub(r"^(the|a|an)\s+","",term.strip(),flags=re.I)
    return re.sub(r"\s+"," ",term).strip(" -–—:;,." )

def _quality_ok(question,answer,distractors):
    q=normalize_text(question); a=normalize_text(answer); ds=[normalize_text(x) for x in distractors]
    if not (30<=len(q)<=500) or not a or len(set(ds))!=3 or a in ds: return False
    if any(not x or len(x)>180 for x in ds): return False
    # Reject placeholder/OCR garbage options.
    if sum(ch.isalnum() for ch in str(answer))<2: return False
    if any(sum(ch.isalnum() for ch in str(x))<2 for x in distractors): return False
    # Options should not be near-identical.
    if any(difflib.SequenceMatcher(None,ds[i],ds[j]).ratio()>0.92 for i in range(3) for j in range(i+1,3)): return False
    return True

def _dedupe_candidates(values, limit=500):
    out=[]; seen=set()
    for v in values:
        v=str(v).strip(" .:;,-")
        k=normalize_text(v)
        if not k or k in seen or len(v)>180: continue
        if any(difflib.SequenceMatcher(None,k,normalize_text(x)).ratio()>0.93 for x in out[-120:]): continue
        seen.add(k); out.append(v)
        if len(out)>=limit: break
    return out

def _select_chunks_for_ai(chunks, char_budget=14000, offset=0):
    """Pick a representative, evenly-spread spread of chunks across the whole
    document (not just the first N) so long PDFs get full coverage instead of
    only being quizzed on their opening pages."""
    if not chunks:
        return []
    total_chars = sum(len(c["text"]) for c in chunks)
    if total_chars <= char_budget:
        return chunks
    n = len(chunks)
    avg_len = max(1, total_chars // n)
    # Evenly-spaced sampling across the whole document (not just the opening
    # pages), so long PDFs still get full-document question coverage.
    approx_slots = max(1, char_budget // avg_len)
    skip = max(1, math.ceil(n / approx_slots))
    start_at = offset % max(1, skip)
    picked, used_chars = [], 0
    for i in range(start_at, n, skip):
        c = chunks[i]
        if used_chars + len(c["text"]) > char_budget and picked:
            break
        picked.append(c)
        used_chars += len(c["text"])
    return picked or chunks[: max(1, char_budget // 1000)]


def _call_anthropic_messages(prompt, max_tokens=4096):
    """Minimal stdlib-only call to the Anthropic Messages API. Returns the
    concatenated text of the response, or raises on any failure."""
    if not ANTHROPIC_API_KEY:
        raise RuntimeError("No ANTHROPIC_API_KEY configured.")
    body = json.dumps({
        "model": ANTHROPIC_MODEL,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")
    req = urllib.request.Request(
        ANTHROPIC_API_URL,
        data=body,
        method="POST",
        headers={
            "content-type": "application/json",
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
        },
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    parts = [b.get("text", "") for b in data.get("content", []) if b.get("type") == "text"]
    return "\n".join(parts)


def _parse_ai_question_json(raw):
    """Extract a JSON array of question objects from a model response, tolerant
    of stray prose or markdown code fences around the JSON."""
    raw = (raw or "").strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    start = raw.find("[")
    end = raw.rfind("]")
    if start == -1 or end == -1 or end < start:
        return []
    try:
        parsed = json.loads(raw[start:end + 1])
    except Exception:
        return []
    return parsed if isinstance(parsed, list) else []


def generate_pdf_questions_ai(pages, subject, topic, max_questions=100, job_id=None):
    """High-quality LLM MCQ engine, strictly grounded in the uploaded PDF text.
    Returns None (signal to fall back to the local engine) if no API key is
    configured or every attempt fails; returns a list (possibly shorter than
    max_questions) otherwise."""
    if not AI_GENERATION_ENABLED:
        return None
    target = max(5, min(int(max_questions or 10), 200))
    chunks = build_study_chunks(pages)
    if not chunks:
        return None
    existing_stems = [q.get("q", "") for q in get_all_questions()]
    generated = []
    BATCH = 25
    attempts = 0
    max_attempts = math.ceil(target / BATCH) + 2
    if job_id:
        _job_update(job_id, progress=78, stage="generating",
                     message="Asking Claude to write grounded questions from your PDF…")
    while len(generated) < target and attempts < max_attempts:
        attempts += 1
        need = min(BATCH, target - len(generated))
        source_chunks = _select_chunks_for_ai(chunks, char_budget=14000, offset=attempts - 1)
        source_text = "\n\n".join(f"[page {c['page']}] {c['text']}" for c in source_chunks)
        avoid = existing_stems + [g["q"] for g in generated]
        avoid_block = ""
        if avoid:
            avoid_block = "Do not repeat or closely rephrase any of these existing questions:\n- " + "\n- ".join(avoid[-40:])
        prompt = f"""You are an expert exam writer creating multiple-choice questions strictly grounded in the SOURCE TEXT below, extracted from a PDF titled "{topic}" (subject: {subject}).

Write {need} high-quality multiple-choice questions. Requirements:
- Every question and its correct answer must be directly supported by the SOURCE TEXT. Never invent facts not present in it.
- Vary question types: definitions, cause/effect, comparisons, application/scenario reasoning, numerical/data recall, "which of the following is true/false", and conceptual understanding. Avoid making every question a simple fill-in-the-blank.
- Each question needs exactly 4 options. Exactly one is correct. The 3 distractors must be plausible, non-trivial, and drawn from the same domain (not random unrelated text) — no "all of the above"/"none of the above".
- Write a short 1-2 sentence explanation for the correct answer, referencing the page number.
- Include the "page" field with the source page number the question is grounded in.
- Skip a question type entirely rather than inventing unsupported content if the source text doesn't support it.
{avoid_block}

SOURCE TEXT:
{source_text}

Respond with ONLY a raw JSON array (no markdown, no commentary), where each item has this exact shape:
{{"q": "question text", "options": ["opt A", "opt B", "opt C", "opt D"], "answer_index": 0, "explanation": "why this is correct", "page": 1}}"""
        try:
            raw = _call_anthropic_messages(prompt, max_tokens=4096)
            items = _parse_ai_question_json(raw)
        except Exception:
            items = []
        if not items:
            continue
        for item in items:
            if len(generated) >= target:
                break
            try:
                qtext = re.sub(r"\s+", " ", str(item.get("q", ""))).strip()
                options = [str(o).strip() for o in (item.get("options") or [])]
                idx = int(item.get("answer_index", -1))
                page = int(item.get("page", 0) or 0)
                explanation = str(item.get("explanation", "")).strip()
            except Exception:
                continue
            if len(options) != 4 or not (0 <= idx < 4):
                continue
            answer = options[idx]
            distractors = [o for i, o in enumerate(options) if i != idx]
            if not _quality_ok(qtext, answer, distractors):
                continue
            if _question_is_duplicate(qtext, existing_stems + [g["q"] for g in generated]):
                continue
            generated.append({
                "id": "pdf_" + secrets.token_hex(8), "subject": subject, "topic": topic,
                "q": qtext, "options": options, "answer": idx, "source": "uploaded PDF",
                "source_page": page, "kind": "ai_grounded",
                "explanation": explanation or f"Based on the uploaded material (page {page}).",
            })
        if job_id:
            _job_update(job_id, progress=min(95, 78 + int(len(generated) / max(1, target) * 17)),
                         stage="generating", message=f"Generated {len(generated)} of {target} AI questions…")
    return generated


def generate_pdf_questions(pages, subject, topic, max_questions=100, job_id=None):
    """Router: use the LLM generator when an API key is configured (much higher
    question quality and variety); always fall back to — or top up with — the
    local source-grounded engine so generation never fails outright."""
    target = max(5, min(int(max_questions or 10), 200))
    ai_questions = []
    if AI_GENERATION_ENABLED:
        try:
            ai_questions = generate_pdf_questions_ai(pages, subject, topic, max_questions=target, job_id=job_id) or []
        except Exception:
            ai_questions = []
    if len(ai_questions) >= target:
        if job_id:
            _job_update(job_id, progress=96, stage="quality_check",
                         message=f"Validated {len(ai_questions)} AI-generated questions")
        return ai_questions
    # Top up any shortfall with the local engine so the user still gets `target`
    # questions even if the AI call partially failed or the source text was thin.
    remaining = target - len(ai_questions)
    if job_id and remaining > 0:
        _job_update(job_id, stage="generating", message=f"Filling remaining {remaining} questions with the local engine…")
    local_questions = generate_pdf_questions_local(pages, subject, topic, max_questions=remaining, job_id=job_id,
                                                    avoid_stems=[q["q"] for q in ai_questions]) if remaining > 0 else []
    combined = ai_questions + local_questions
    if job_id:
        _job_update(job_id, progress=96, stage="quality_check", message=f"Validated {len(combined)} high-quality questions")
    return combined


def generate_pdf_questions_local(pages, subject, topic, max_questions=100, job_id=None, avoid_stems=None):
    """Source-grounded local MCQ engine (no API key required). Generates diverse candidates, validates them, then selects the best target count."""
    target=max(5,min(int(max_questions or 10),200))
    facts,records=_extract_candidate_facts(pages)
    existing_stems=[q.get("q","") for q in get_all_questions()]+list(avoid_stems or [])
    generated=[]; used_kinds={}; started=time.time()

    defs=facts["definitions"]; terms=facts["terms"]; units=facts["units"]; formulas=facts["formulas"]
    term_pool=_dedupe_candidates([x[0] for x in defs]+[x[1] for x in terms])
    def_pool=_dedupe_candidates([x[1] for x in defs])
    unit_pool=_dedupe_candidates([x[1] for x in units])
    formula_pool=_dedupe_candidates([x[1] for x in formulas])
    all_sent=[r["text"] for r in records]
    statement_pool=_dedupe_candidates([x for x in all_sent if 55<=len(x)<=260],limit=800)

    def add(qtext,answer,pool,source_page=0,kind="concept",explanation=""):
        if len(generated)>=target: return False
        qtext=re.sub(r"\s+"," ",str(qtext)).strip()
        answer=str(answer).strip(" .:;,-")
        if not qtext or not answer: return False
        if _question_is_duplicate(qtext,existing_stems+[x["q"] for x in generated]): return False
        # Prefer candidates that are category-compatible with the answer.
        distractors=[]; used={normalize_text(answer)}
        vals=list(pool); random.shuffle(vals)
        for value in vals:
            value=str(value).strip(" .:;,-"); k=normalize_text(value)
            if not k or k in used or len(value)>180: continue
            if any(difflib.SequenceMatcher(None,k,normalize_text(x)).ratio()>=0.88 for x in distractors): continue
            used.add(k); distractors.append(value)
            if len(distractors)==3: break
        if len(distractors)<3 or not _quality_ok(qtext,answer,distractors): return False
        opts=[answer]+distractors; random.shuffle(opts)
        generated.append({"id":"pdf_"+secrets.token_hex(8),"subject":subject,"topic":topic,"q":qtext,"options":opts,"answer":opts.index(answer),"source":"uploaded PDF","source_page":source_page,"kind":kind,"explanation":explanation or f"Based on the uploaded material (page {source_page})."})
        used_kinds[kind]=used_kinds.get(kind,0)+1
        return True

    # Multiple passes intentionally balance question families instead of filling with one template.
    for term,definition,page in defs:
        add(f"Which statement best defines {term}?",definition,def_pool,page,"definition",f"The material defines {term} as {definition}.")
        if len(generated)>=target: break
        add(f"Which term matches this description: {definition}?",term,term_pool,page,"definition_reverse",f"The described concept is {term}.")

    for desc,term,page in terms:
        if len(generated)>=target: break
        add(f"The material describes {desc}. What is this concept called?",term,term_pool,page,"terminology",f"The material calls this {term}.")

    for quantity,unit,page in units:
        if len(generated)>=target: break
        add(f"What is the SI unit of {quantity}?",unit,unit_pool,page,"unit",f"The material gives {unit} as the SI unit of {quantity}.")

    for name,formula,page in formulas:
        if len(generated)>=target: break
        add(f"Which expression represents {name}?",formula,formula_pool,page,"formula",f"The formula given in the material is {formula}.")

    # Proportionality and directional relationships.
    rel_pool=["directly proportional","inversely proportional","increases","decreases","remains constant","depends on"]
    for sent,page in facts["relations"]:
        if len(generated)>=target: break
        m=re.search(r"(.{2,90}?)\s+(directly proportional|inversely proportional)\s+to\s+(.{2,90})",sent,re.I)
        if m:
            add(f"According to the material, how is {m.group(1).strip()} related to {m.group(3).strip()}?",m.group(2).lower(),rel_pool,page,"relationship",sent)
        else:
            # Use a concise blank around an explicit directional verb.
            m=re.search(r"\b(increases|decreases)\b",sent,re.I)
            if m:
                masked=sent[:m.start()]+"_____"+sent[m.end():]
                add(f"Complete the relationship stated in the material: {masked}",m.group(1).lower(),["increases","decreases","remains constant","becomes zero"],page,"relationship",sent)

    # Numeric recall only when the sentence is meaningful, not as random OCR trivia.
    numeric_pool=[]
    for sent,page in facts["numbers"]:
        for val in re.findall(r"\b\d+(?:\.\d+)?(?:\s*[×x]\s*10\s*[−-]?\s*\d+)?(?:\s*%|\s*[A-Za-zΩμ°]+)?\b",sent):
            numeric_pool.append(val.strip())
    numeric_pool=_dedupe_candidates(numeric_pool,250)
    for sent,page in facts["numbers"]:
        if len(generated)>=target: break
        vals=re.findall(r"\b\d+(?:\.\d+)?(?:\s*[×x]\s*10\s*[−-]?\s*\d+)?(?:\s*%|\s*[A-Za-zΩμ°]+)?\b",sent)
        if not vals: continue
        answer=vals[0].strip(); masked=re.sub(re.escape(answer),"_____",sent,count=1)
        if 45<=len(masked)<=280:
            add(f"Which value correctly completes the statement from the material? {masked}",answer,numeric_pool,page,"numerical",f"The source sentence on page {page} gives the value {answer}.")

    # Conceptual fill-in: select important multi-word terms, not arbitrary long words.
    concept_terms=_dedupe_candidates([x[0] for x in defs]+[x[1] for x in terms]+[w for r in records for w in re.findall(r"\b[A-Za-z][A-Za-z-]{5,}\b",r["text"])],500)
    for r in records:
        if len(generated)>=target: break
        sent=r["text"]; page=r["page"]
        candidates=[t for t in concept_terms if 4<=len(t.split())<=6 and re.search(r"\b"+re.escape(t)+r"\b",sent,re.I)]
        if not candidates: continue
        answer=max(candidates,key=lambda x:(len(x.split()),len(x)))
        masked=re.sub(r"\b"+re.escape(answer)+r"\b","_____",sent,count=1,flags=re.I)
        if 45<=len(masked)<=280:
            pool=[x for x in concept_terms if x!=answer]
            add(f"Which term correctly completes this statement? {masked}",answer,pool,page,"concept",sent)

    # High-value statement questions: use a topic anchor in the stem and sentence alternatives from the same document.
    # This avoids the old generic repeated 'Which statement is supported...' stem.
    anchors=[]
    for r in records:
        words=re.findall(r"\b[A-Za-z][A-Za-z-]{4,}\b",r["text"])
        if words:
            anchors.append((max(words,key=len),r["text"],r["page"]))
    random.shuffle(anchors)
    for anchor,sent,page in anchors:
        if len(generated)>=target: break
        related=[x for x in statement_pool if normalize_text(x)!=normalize_text(sent) and anchor.lower() in x.lower()]
        if len(related)<3: continue
        add(f"Which statement about {anchor} is supported by the uploaded material?",sent,related[:12],page,"comprehension",sent)

    # If the document supports fewer questions, do not manufacture facts.
    if job_id:
        elapsed=max(0.1,time.time()-started)
        _job_update(job_id,progress=96,stage="quality_check",message=f"Validated {len(generated)} high-quality questions",eta_seconds=1)
    return generated


def _process_pdf_job(job_id, raw, filename, subject, topic, owner, target_questions):
    try:
        _job_update(job_id,status="processing",progress=3,stage="starting",message="Preparing PDF…",target_questions=target_questions)
        pages,page_count,ocr_pages=extract_pdf_text(raw,job_id=job_id)
        text="\n\n".join(p.get("text","") for p in pages)
        words=len(re.findall(r"\b\w+\b",text))
        if words<20:
            if not _tesseract_path:
                raise ValueError("This PDF appears to be scanned/image-only, but OCR is unavailable in the server image.")
            raise ValueError("No readable text was found. Try a clearer PDF or a scan with visible text.")
        _job_update(job_id,progress=72,stage="indexing",message=f"Indexed {words:,} words across {page_count} pages…",extracted_words=words)
        chunks=build_study_chunks(pages)
        _job_update(job_id,progress=76,stage="generating",message=f"Generating up to {target_questions} source-grounded MCQs…",chunks=len(chunks),eta_seconds=max(2,round(len(pages)*0.2)))
        questions=generate_pdf_questions(pages,subject,topic,max_questions=target_questions,job_id=job_id)
        if not questions:
            raise ValueError("Text was extracted, but there was not enough reliable structured content to make MCQs.")
        for q in questions:
            q["owner"]=owner or "unknown"; q["source"]=filename
        with upload_lock:
            # Cross-set duplicate protection: compare normalized and fuzzy stems globally.
            existing_stems=[q.get("q","") for q in get_all_questions()]
            new_questions=[]
            for q in questions:
                if not _question_is_duplicate(q.get("q","") ,existing_stems+[x.get("q","") for x in new_questions]):
                    new_questions.append(q)
        with upload_lock:
            uploaded_questions.extend(new_questions); save_uploaded_questions()
        actual=len(new_questions)
        msg=(f"Created {actual} of {target_questions} requested questions from {filename}." if actual<target_questions else f"Created all {actual} requested questions from {filename}.")
        _job_update(job_id,status="complete",progress=100,stage="complete",message=msg,filename=filename,subject=subject,topic=topic,pages=page_count,ocr_pages=ocr_pages,extracted_words=words,chunks=len(chunks),questions_added=actual,target_questions=target_questions)
    except ValueError as e:
        _job_update(job_id,status="error",progress=100,stage="error",message=str(e))
    except Exception as e:
        _job_update(job_id,status="error",progress=100,stage="error",message=f"Could not process this PDF: {e}")


@app.route("/api/upload_pdf", methods=["POST"])
def upload_pdf():
    if "pdf" not in request.files:
        return jsonify(success=False,message="Choose a PDF file first."),400
    file=request.files["pdf"]; filename=secure_filename(file.filename or "")
    if not filename.lower().endswith(".pdf"):
        return jsonify(success=False,message="Only PDF files are accepted."),400
    subject=str(request.form.get("subject") or "General").strip()[:60] or "General"
    topic=str(request.form.get("topic") or os.path.splitext(filename)[0] or "Uploaded PDF").strip()[:100] or "Uploaded PDF"
    try: target=max(5,min(int(request.form.get("question_count",10) or 10),200))
    except Exception: target=10
    raw=file.read(MAX_PDF_BYTES+1)
    if len(raw)>MAX_PDF_BYTES: return jsonify(success=False,message="PDF is larger than the 100 MB limit."),413
    if not raw.startswith(b"%PDF-"): return jsonify(success=False,message="That file is not a valid PDF."),400
    if fitz is None: return jsonify(success=False,message="PDF engine is unavailable. Check deployment dependencies."),500
    owner=clean_name(request.form.get("username")); job_id=secrets.token_urlsafe(12)
    with pdf_jobs_lock:
        pdf_jobs[job_id]={"status":"queued","progress":1,"stage":"queued","message":"PDF uploaded. Waiting for processor…","created_at":time.time(),"updated_at":time.time(),"target_questions":target}
    threading.Thread(target=_process_pdf_job,args=(job_id,raw,filename,subject,topic,owner,target),daemon=True).start()
    return jsonify(success=True,job_id=job_id,message="PDF accepted. Processing started.",target_questions=target)

@app.route("/api/pdf_job/<job_id>", methods=["GET"])
def pdf_job(job_id):
    with pdf_jobs_lock:
        job=copy.deepcopy(pdf_jobs.get(job_id))
    if not job:
        return jsonify(success=False,message="PDF job not found or expired."),404
    return jsonify(success=True,job=job)


@app.route("/api/uploaded_questions", methods=["GET"])
def api_uploaded_questions():
    with upload_lock:
        return jsonify(success=True, count=len(uploaded_questions), questions=uploaded_questions)

def get_all_questions():
    return uploaded_questions

def get_catalog(username=""):
    username = clean_name(username)
    grouped = {}
    for q in get_all_questions():
        subject = q.get("subject", "General")
        topic = q.get("topic", "General")
        key = (subject, topic)
        item = grouped.setdefault(key, {"subject": subject, "topic": topic, "count": 0, "owners": set()})
        item["count"] += 1
        owner = str(q.get("owner") or "").strip().lower()
        if owner:
            item["owners"].add(owner)
    catalog = {}
    for (subject, topic), item in sorted(grouped.items(), key=lambda x: (x[0][0].lower(), x[0][1].lower())):
        owners = item["owners"]
        # A set can be deleted only by its owner. Legacy sets without an owner are not deletable.
        owned = bool(username) and username.lower() in owners and len(owners) == 1
        catalog.setdefault(subject, []).append({
            "topic": topic,
            "count": item["count"],
            "deletable": owned,
        })
    return catalog

def prepare_questions(raw_questions):
    """Make room-specific copies and shuffle answer options so the correct choice
    is not always in the same position. The answer index is updated safely."""
    prepared = []
    for original in raw_questions:
        q = copy.deepcopy(original)
        correct_text = q["options"][q["answer"]]
        random.shuffle(q["options"])
        q["answer"] = q["options"].index(correct_text)
        prepared.append(q)
    return prepared

def _deck_key(pool):
    """Create a stable key for a question pool so each topic gets its own deck."""
    return tuple(sorted(str(q.get("id", "")) for q in pool))


def _deal_random_questions(pool, amount):
    """Deal questions from a shuffled deck without immediate/recent repeats.

    Each subject/topic pool has its own deck. A question is removed from the deck
    when dealt and only becomes available again after that pool is exhausted.
    This gives much stronger randomization than random.sample() for repeated
    battles on the same topic.
    """
    if not pool:
        return []

    amount = max(1, min(int(amount), len(pool)))
    key = _deck_key(pool)
    pool_by_id = {str(q.get("id", "")): q for q in pool}

    deck = QUESTION_DECKS.get(key)
    if not deck or any(qid not in pool_by_id for qid in deck):
        deck = list(pool_by_id.keys())
        random.shuffle(deck)
        QUESTION_DECKS[key] = deck

    chosen_ids = []
    while len(chosen_ids) < amount:
        if not deck:
            # The complete pool has been used. Start a fresh random cycle.
            deck.extend(pool_by_id.keys())
            random.shuffle(deck)

        take = min(amount - len(chosen_ids), len(deck))
        chosen_ids.extend(deck[:take])
        del deck[:take]

    return [pool_by_id[qid] for qid in chosen_ids]


def choose_questions_from_selection(selections, amount, battle_mode):
    allq=get_all_questions()
    selected=[]
    wanted={(str(x.get("subject","")).strip(), str(x.get("topic","")).strip()) for x in (selections or [])}
    for q in allq:
        if (q.get("subject"), q.get("topic")) in wanted:
            selected.append(q)
    if not selected:
        return choose_questions("mixed", amount, battle_mode)

    amount=max(5, min(int(amount), len(selected)))
    chosen=_deal_random_questions(selected, amount)
    chosen=prepare_questions(chosen)
    return chosen, "Multiple Subjects" if len({q["subject"] for q in selected})>1 else selected[0]["subject"], "Multiple Topics" if len({(q["subject"],q["topic"]) for q in selected})>1 else selected[0]["topic"]


def load_progress():
    global players
    if not os.path.exists(SAVE_FILE):
        players = {}
        return
    try:
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            players = json.load(f)
    except Exception:
        players = {}

def save_progress():
    # Atomic save: prevents the progress file from being left half-written.
    tmp = SAVE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(players, f, indent=2)
    os.replace(tmp, SAVE_FILE)

def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        120000
    ).hex()
    return salt + "$" + digest

def verify_password(password, stored):
    try:
        salt, digest = stored.split("$", 1)
        check = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            120000
        ).hex()
        return secrets.compare_digest(check, digest)
    except Exception:
        return False

def clean_username(name):
    return re.sub(r"[^A-Za-z0-9_]", "", str(name or "").strip())[:24]

def get_player(name):
    if name not in players:
        players[name] = {
            "password_hash": None,
            "xp": 0, "wins": 0, "battles": 0,
            "attempted": 0, "correct": 0, "accuracy": 0,
            "best_score": 0, "best_streak": 0,
            "win_streak": 0, "coins": 0, "level": 1,
            "achievements": [], "champion": False, "champion_wins": 0,
            "history": [], "session_wins": 0
        }
    else:
        # Keep old V6 progress files compatible.
        players[name].setdefault("password_hash", None)
        players[name].setdefault("xp", 0)
        players[name].setdefault("wins", 0)
        players[name].setdefault("battles", 0)
        players[name].setdefault("attempted", 0)
        players[name].setdefault("correct", 0)
        players[name].setdefault("accuracy", 0)
        players[name].setdefault("best_score", 0)
        players[name].setdefault("best_streak", 0)
        players[name].setdefault("win_streak", 0)
        players[name].setdefault("coins", 0)
        players[name].setdefault("level", max(1, players[name].get("xp", 0)//100 + 1))
        players[name].setdefault("achievements", [])
        players[name].setdefault("champion", False)
        players[name].setdefault("champion_wins", 0)
        players[name].setdefault("history", [])
        players[name].setdefault("session_wins", 0)
    return players[name]

def clean_name(name):
    return clean_username(name)

def generate_code():
    while True:
        c = "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
        if c not in rooms:
            return c

def update_achievement(d, achievement):
    d.setdefault("achievements", [])
    if achievement not in d["achievements"]:
        d["achievements"].append(achievement)

def refresh_level(d):
    d["level"] = max(1, int(d.get("xp", 0)) // 100 + 1)

def apply_winner_rewards(d):
    d["coins"] = d.get("coins", 0) + 100
    d["win_streak"] = d.get("win_streak", 0) + 1
    d["champion"] = True
    d["champion_wins"] = d.get("champion_wins", 0) + 1
    update_achievement(d, "🏆 First Victory")
    update_achievement(d, "👑 Champion")
    if d["win_streak"] >= 3:
        update_achievement(d, "🔥 Unstoppable (3 Win Streak)")
    if d["win_streak"] >= 5:
        update_achievement(d, "🔥 Legendary (5 Win Streak)")
    if d.get("wins", 0) >= 5:
        update_achievement(d, "👑 5-Time Champion")
    refresh_level(d)

def make_player(name):
    return {
        "name": name,
        "score": 0,
        "correct": 0,
        "answered": 0,
        "answer_index": -1,
        "current_answer": None,
        "streak": 0,
        "best_streak": 0,
        "elimination_warning": False,
        "eliminated": False,
        "session_score": 0,
        "max_speed_bonus": 0,
        "rank_before": None
    }

def player_public_data(p):
    return {
        "name": p["name"],
        "score": p["score"],
        "correct": p["correct"],
        "answered": p["answered"],
        "answer_index": p["answer_index"],
        "streak": p["streak"],
        "best_streak": p["best_streak"],
        "elimination_warning": p["elimination_warning"],
        "eliminated": p["eliminated"],
        "session_score": p.get("session_score", 0)
    }

def public_room(room):
    out = {
        "code": room["code"],
        "host": room["host"],
        "players": [player_public_data(p) for p in room["players"]],
        "status": room["status"],
        "question_index": room["question_index"],
        "total_questions": len(room["questions"]),
        "question_started": room.get("question_started", 0),
        "subject": room["subject"],
        "topic": room["topic"],
        "selections": room.get("selections", []),
        "battle_mode": room.get("battle_mode", "classic"),
        "question_time": room.get("question_time", QUESTION_TIME),
        "is_final_question": room["question_index"] == len(room["questions"]) - 1 if room["questions"] else False,
        "chat": room.get("chat", [])[-100:],
        "dare": room.get("dare"),
        "dare_player": room.get("dare_player"),
        "dares_list": DARE_LIST,
        "rewards": room.get("rewards", {}),
        "winner": room.get("winner"),
        "finished_at": room.get("finished_at", 0),
        "intro_started": room.get("intro_started", 0),
        "intro_duration": room.get("intro_duration", 10),
        "session_battles": room.get("session_battles", 1),
        "session_battle": room.get("session_battle", 1),
        "session_scores": room.get("session_scores", {}),
        "session_stats": room.get("session_stats", {}),
        "battle_awards": room.get("battle_awards", []),
        "session_special_awards": room.get("session_special_awards", []),
        "session_champion": room.get("session_champion"),
        "session_finished": room.get("session_finished", False),
        "surprise": room.get("surprise"),
        "surprise_history": room.get("surprise_history", []),
        "session_awards": room.get("session_awards", []),
        "session_last_place": room.get("session_last_place")
    }
    if room["status"] == "playing" and room["question_index"] < len(room["questions"]):
        q = room["questions"][room["question_index"]]
        out["question"] = {"q": q["q"], "options": q["options"], "subject": q["subject"], "topic": q["topic"]}
    return out

def choose_questions(mode, amount, battle_mode):
    if mode == "halogen":
        pool = [q for q in uploaded_questions if q.get("subject") == "Chemistry"]
        subject = "Chemistry"
        topic = "Halogen Derivatives"
    elif mode == "fluids":
        pool = [q for q in uploaded_questions if q.get("subject") == "Physics"]
        subject = "Physics"
        topic = "Mechanical Properties of Fluids"
    else:
        pool = uploaded_questions[:]
        subject = "Mixed"
        topic = "Halogen + Fluids"

    amount = max(5, min(int(amount), len(pool)))

    return prepare_questions(_deal_random_questions(pool, amount)), subject, topic

def finish_room(room):
    if room.get("status") == "finished":
        return

    hidden_names = {str(x).strip().lower() for x in HALL_OF_FAME_HIDDEN_NAMES}
    is_tournament = room.get("battle_mode") == "tournament"
    ranked = sorted(room["players"], key=lambda p: (p["score"], p["correct"]), reverse=True)
    room["rewards"] = {}
    winner_name = ranked[0]["name"] if ranked else None

    # Testing accounts remain hidden from the public Hall of Fame, but are fully eligible in Tournament Mode for testing.
    eligible_ranked = ranked if is_tournament else [p for p in ranked if p["name"].strip().lower() not in hidden_names]
    awards = []
    # Tournament awards are intentionally NOT calculated per battle. They are based
    # on the player's accumulated performance across the whole session and are
    # revealed only after the final tournament battle.
    if not is_tournament and eligible_ranked:
        top_acc = max((p["correct"] / p["answered"] * 100) if p["answered"] else 0 for p in eligible_ranked)
        top_streak = max((p.get("best_streak", 0) for p in eligible_ranked), default=0)
        top_speed = max((p.get("max_speed_bonus", 0) for p in eligible_ranked), default=0)
        for p in eligible_ranked:
            acc = (p["correct"] / p["answered"] * 100) if p["answered"] else 0
            if acc == top_acc and top_acc > 0:
                awards.append({"name": p["name"], "award": "🧠 Brain Master", "reason": f"{round(acc)}% accuracy"})
            if p.get("best_streak", 0) == top_streak and top_streak >= 3:
                awards.append({"name": p["name"], "award": "🔥 Streak King", "reason": f"{top_streak} streak"})
            if p.get("max_speed_bonus", 0) == top_speed and top_speed >= 3:
                awards.append({"name": p["name"], "award": "⚡ Speed Demon", "reason": "Lightning-fast answer"})

    room["battle_awards"] = awards if not is_tournament else []
    for pos, rp in enumerate(ranked):
        d = get_player(rp["name"])
        d["xp"] += rp["score"]
        d["battles"] += 1
        d["attempted"] += rp["answered"]
        d["correct"] += rp["correct"]
        d["best_score"] = max(d["best_score"], rp["score"])
        d["best_streak"] = max(d.get("best_streak", 0), rp["best_streak"])
        if d["attempted"]:
            d["accuracy"] = round(d["correct"] / d["attempted"] * 100, 1)
        rp["session_score"] = rp.get("session_score", 0) + rp["score"]
        room.setdefault("session_scores", {})[rp["name"]] = rp["session_score"]
        if is_tournament:
            ss = room.setdefault("session_stats", {}).setdefault(rp["name"], {
                "correct": 0, "answered": 0, "best_streak": 0,
                "max_speed_bonus": 0, "battle_wins": 0, "battles_played": 0
            })
            ss["correct"] += rp.get("correct", 0)
            ss["answered"] += rp.get("answered", 0)
            ss["best_streak"] = max(ss.get("best_streak", 0), rp.get("best_streak", 0))
            ss["max_speed_bonus"] = max(ss.get("max_speed_bonus", 0), rp.get("max_speed_bonus", 0))
            ss["battles_played"] += 1
            if pos == 0:
                ss["battle_wins"] += 1
        if pos == 0:
            d["wins"] += 1
            apply_winner_rewards(d)
            room["rewards"][rp["name"]] = {
                "xp_bonus": 0, "coins": 100, "win_streak": d["win_streak"],
                "level": d["level"], "title": "👑 Champion"
            }
        else:
            d["win_streak"] = 0
            d["champion"] = False
            refresh_level(d)

        acc = round((rp["correct"] / rp["answered"] * 100), 1) if rp["answered"] else 0
        my_awards = [a["award"] for a in awards if a["name"].lower() == rp["name"].lower()]
        d.setdefault("history", []).append({
            "date": time.strftime("%Y-%m-%d %H:%M"),
            "topic": room.get("topic", "Mixed"),
            "score": rp["score"], "position": pos + 1,
            "correct": rp["correct"], "answered": rp["answered"],
            "accuracy": acc, "best_streak": rp["best_streak"],
            "awards": my_awards,
            "session": room.get("session_battle", 1)
        })
        d["history"] = d["history"][-30:]

    is_final_session = (not is_tournament) or (room.get("session_battle", 1) >= room.get("session_battles", 1))

    # Dares happen ONLY once, after the complete tournament session.
    # For a normal single battle, the existing end-of-battle dare remains.
    room["dare"] = None
    room["dare_player"] = None
    if is_final_session and room.get("players"):
        if is_tournament:
            totals = list(room.get("session_scores", {}).items())
            totals.sort(key=lambda x: x[1])
            if totals:
                room["session_last_place"] = totals[0][0]
                room["dare_player"] = totals[0][0]
                room["dare"] = random.choice(DARE_LIST)
        elif ranked:
            real_ranked = [p for p in ranked if p["name"].strip().lower() not in hidden_names]
            if real_ranked:
                room["dare_player"] = real_ranked[-1]["name"]
                room["dare"] = random.choice(DARE_LIST)

    room["winner"] = winner_name
    room["status"] = "finished"
    room["finished_at"] = time.time()

    if is_final_session:
        room["session_finished"] = True
        totals = list(room.get("session_scores", {}).items()) if is_tournament else [(n, v) for n, v in room.get("session_scores", {}).items() if n.strip().lower() not in hidden_names]
        totals.sort(key=lambda x: x[1], reverse=True)
        room["session_champion"] = totals[0][0] if totals else None
        room["session_awards"] = []
        room["session_special_awards"] = []
        if totals:
            champ = get_player(totals[0][0])
            champ["session_wins"] = champ.get("session_wins", 0) + 1
            update_achievement(champ, "🏟️ Session Champion")
            room["session_awards"].append({"name": totals[0][0], "award": "👑 Session Champion", "value": totals[0][1]})

        if is_tournament:
            # Overall-session special awards: use cumulative tournament statistics,
            # never a single battle's result.
            session_stats = room.get("session_stats", {})
            ranked_names = [n for n, _ in totals]
            session_special = []
            valid_stats = [(n, session_stats.get(n, {})) for n in ranked_names if n in session_stats]
            if valid_stats:
                def acc_of(item):
                    st=item[1]; return (st.get("correct",0)/st.get("answered",0)*100) if st.get("answered",0) else 0
                top_acc=max(acc_of(x) for x in valid_stats)
                top_streak=max(st.get("best_streak",0) for _,st in valid_stats)
                top_speed=max(st.get("max_speed_bonus",0) for _,st in valid_stats)
                for n, st in valid_stats:
                    acc=acc_of((n,st))
                    if top_acc > 0 and acc == top_acc:
                        session_special.append({"name":n,"award":"🧠 Brain Master","reason":f"{round(acc)}% tournament accuracy"})
                    if top_streak >= 3 and st.get("best_streak",0) == top_streak:
                        session_special.append({"name":n,"award":"🔥 Streak King","reason":f"{top_streak} best streak across the tournament"})
                    if top_speed >= 3 and st.get("max_speed_bonus",0) == top_speed:
                        session_special.append({"name":n,"award":"⚡ Speed Demon","reason":"Fastest answers across the tournament"})
                room["session_special_awards"] = session_special
                room["session_awards"].extend(session_special)
                # Attach the final-session awards to the player's latest history entry.
                for a in session_special:
                    for dname in [a["name"]]:
                        account=get_player(dname)
                        if account.get("history"):
                            account["history"][-1].setdefault("awards", []).append(a["award"])
    else:
        room["session_finished"] = False
        room["session_champion"] = None
        room["session_awards"] = []
        room["session_special_awards"] = []

    save_progress()

def advance_room(room):
    if room["status"] != "playing":
        return
    
    # Check for elimination warning logic before proceeding
    if room["question_index"] < len(room["questions"]) - 1:
        ranked = sorted(room["players"], key=lambda p: (p["score"], p["correct"]))
        if ranked:
            lowest_score = ranked[0]["score"]
            for p in room["players"]:
                p["elimination_warning"] = (p["score"] == lowest_score)
    
    room["question_index"] += 1
    if room["question_index"] >= len(room["questions"]):
        finish_room(room)
        return
    room["question_started"] = time.time()
    for p in room["players"]:
        p["answer_index"] = -1
        p["current_answer"] = None



# ============================================================
# MULTIPLAYER BOSS BATTLE
# ============================================================
BOSS_MAX_HP = 1000
BOSS_DAMAGE = 50
BOSS_FAST_BONUS = 20

def ensure_boss(room):
    """Create/reset the cooperative boss state for a room."""
    if "boss" not in room:
        room["boss"] = {
            "name": "StudyBattle Boss",
            "max_hp": BOSS_MAX_HP,
            "hp": BOSS_MAX_HP,
            "active": False,
            "defeated": False,
            "damage": {},
            "started_at": None
        }
    return room["boss"]

def boss_start(room):
    boss = ensure_boss(room)
    boss["hp"] = boss["max_hp"]
    boss["active"] = True
    boss["defeated"] = False
    boss["damage"] = {}
    boss["started_at"] = time.time()
    return boss

def boss_deal_damage(room, player_name, fast=False):
    boss = ensure_boss(room)
    if not boss["active"] or boss["defeated"]:
        return boss

    amount = BOSS_DAMAGE + (BOSS_FAST_BONUS if fast else 0)
    boss["hp"] = max(0, boss["hp"] - amount)
    boss["damage"][player_name] = boss["damage"].get(player_name, 0) + amount

    if boss["hp"] <= 0:
        boss["hp"] = 0
        boss["active"] = False
        boss["defeated"] = True

    return boss

@app.route("/api/boss_state", methods=["POST"])
def api_boss_state():
    data = request.get_json() or {}
    code = str(data.get("code", "")).strip().upper()

    with lock:
        room = rooms.get(code)
        if not room:
            return jsonify({"ok": False, "error": "Room not found"}), 404

        boss = ensure_boss(room)
        return jsonify({"ok": True, "boss": boss})

@app.route("/api/boss_start", methods=["POST"])
def api_boss_start():
    data = request.get_json() or {}
    code = str(data.get("code", "")).strip().upper()

    with lock:
        room = rooms.get(code)
        if not room:
            return jsonify({"ok": False, "error": "Room not found"}), 404

        # Boss can be started by the host or when the battle begins.
        boss = boss_start(room)
        room["game_mode"] = "boss"
        return jsonify({"ok": True, "boss": boss})

@app.route("/api/boss_attack", methods=["POST"])
def api_boss_attack():
    data = request.get_json() or {}
    code = str(data.get("code", "")).strip().upper()
    player = str(data.get("name", "")).strip()
    fast = bool(data.get("fast", False))

    if not player:
        return jsonify({"ok": False, "error": "Player name required"}), 400

    with lock:
        room = rooms.get(code)
        if not room:
            return jsonify({"ok": False, "error": "Room not found"}), 404

        if player not in players or players[player].get("room") != code:
            return jsonify({"ok": False, "error": "Player is not in this room"}), 403

        boss = boss_deal_damage(room, player, fast=fast)
        return jsonify({
            "ok": True,
            "boss": boss,
            "defeated": boss["defeated"]
        })


@app.route("/api/pdf_diagnostics", methods=["GET"])
def api_pdf_diagnostics():
    return jsonify({
        "success": True,
        "pymupdf": bool(fitz),
        "pytesseract": bool(pytesseract),
        "pillow": bool(Image),
        "tesseract_path": _tesseract_path or "",
        "tesseract_available": bool(_tesseract_path),
        "max_pdf_mb": MAX_PDF_BYTES // (1024 * 1024),
        "max_pdf_pages": MAX_PDF_PAGES,
        "async_processing": True,
        "progress_endpoint": "/api/pdf_job/<job_id>",
        "ocr_render_scale": OCR_RENDER_SCALE,
        "ai_generation_enabled": AI_GENERATION_ENABLED,
        "ai_model": ANTHROPIC_MODEL if AI_GENERATION_ENABLED else None,
        "ai_note": ("AI-grounded question generation is active." if AI_GENERATION_ENABLED
                     else "Set ANTHROPIC_API_KEY in the environment to enable AI-grounded question generation; using the local generator until then.")
    })


@app.route("/api/features", methods=["GET"])
def api_features_ultimate():
    return jsonify({
        "max_players": 15,
        "question_counts": QUESTION_COUNTS,
        "pdf_question_counts": PDF_QUESTION_COUNTS,
        "features": ULTIMATE_FEATURES
    })


@app.route("/")
def home():
    return render_template_string(HTML)


@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    username = clean_username(data.get("username"))
    password = str(data.get("password") or "")

    if len(username) < 3:
        return jsonify(success=False, message="Username must be at least 3 characters.")
    if len(password) < 4:
        return jsonify(success=False, message="Password must be at least 4 characters.")

    with lock:
        account = players.get(username)

        # If this username already existed in old V6, preserve its progress
        # and let the owner attach a password to it.
        if account:
            get_player(username)
            if account.get("password_hash"):
                return jsonify(success=False, message="Username already exists. Please login.")
            account["password_hash"] = hash_password(password)
        else:
            get_player(username)
            players[username]["password_hash"] = hash_password(password)

        save_progress()
        safe = dict(players[username])
        safe.pop("password_hash", None)

    return jsonify(success=True, username=username, player=safe)


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    username = clean_username(data.get("username"))
    password = str(data.get("password") or "")

    with lock:
        account = players.get(username)

        if not account:
            return jsonify(success=False, message="Account not found. Tap Create Account.")
        if not account.get("password_hash"):
            return jsonify(success=False, message="This is an old V6 account. Tap Create Account once to set its password.")
        if not verify_password(password, account["password_hash"]):
            return jsonify(success=False, message="Wrong username or password.")

        safe = dict(account)
        safe.pop("password_hash", None)

    return jsonify(success=True, username=username, player=safe)


@app.route("/api/profile")
def profile():
    username = clean_username(request.args.get("username"))

    with lock:
        account = players.get(username)
        if not account:
            return jsonify(success=False, message="Player not found.")

        safe = dict(account)
        safe.pop("password_hash", None)

    return jsonify(success=True, username=username, player=safe)



@app.route("/api/catalog")
def api_catalog():
    username = clean_name(request.args.get("username"))
    with upload_lock:
        return jsonify(success=True, catalog=get_catalog(username))


@app.route("/api/delete_study_set", methods=["POST"])
def delete_study_set():
    data = request.get_json() or {}
    username = clean_name(data.get("username"))
    subject = str(data.get("subject") or "").strip()[:60]
    topic = str(data.get("topic") or "").strip()[:100]
    if not username or not subject or not topic:
        return jsonify(success=False, message="Username, subject and topic are required."), 400
    with upload_lock:
        matches = [q for q in uploaded_questions if q.get("subject") == subject and q.get("topic") == topic]
        if not matches:
            return jsonify(success=False, message="Study set not found."), 404
        owners = {str(q.get("owner") or "").strip().lower() for q in matches}
        if owners != {username.lower()}:
            return jsonify(success=False, message="You can delete only study sets you uploaded."), 403
        before = len(uploaded_questions)
        uploaded_questions[:] = [q for q in uploaded_questions if not (q.get("subject") == subject and q.get("topic") == topic and str(q.get("owner") or "").strip().lower() == username.lower())]
        removed = before - len(uploaded_questions)
        save_uploaded_questions()
        # Any cached deck may contain deleted question IDs, so reset the small in-memory deck cache.
        with QUESTION_DECK_LOCK:
            QUESTION_DECKS.clear()
    return jsonify(success=True, removed=removed, message=f"Deleted {subject} → {topic}.")


@app.route("/api/practice_questions", methods=["POST"])
def practice_questions():
    data = request.get_json() or {}
    username = clean_name(data.get("username"))
    selections = data.get("selections", [])
    amount = max(5, min(int(data.get("amount", 10) or 10), 50))
    if not username:
        return jsonify(success=False, message="Please log in first."), 401
    if not isinstance(selections, list):
        selections = []
    try:
        if selections:
            qs, subject, topic = choose_questions_from_selection(selections, amount, "classic")
        else:
            qs, subject, topic = choose_questions("mixed", amount, "classic")
        if not qs:
            return jsonify(success=False, message="No questions found. Upload a study set first."), 404
        # Practice is intentionally separate from multiplayer scoring.
        safe_questions = []
        for q in qs:
            safe_questions.append({
                "id": q.get("id"), "q": q.get("q"), "options": q.get("options", []),
                "answer": q.get("answer", 0), "subject": q.get("subject", subject),
                "topic": q.get("topic", topic)
            })
        return jsonify(success=True, questions=safe_questions, subject=subject, topic=topic)
    except Exception as e:
        return jsonify(success=False, message="Could not prepare practice questions."), 500

TOURNAMENT_SURPRISES = [
    {"id":"double_xp", "name":"💎 DOUBLE XP", "description":"All points earned this battle are doubled.", "multiplier":2, "question_time":QUESTION_TIME},
    {"id":"speed_round", "name":"⚡ SPEED ROUND", "description":"Questions have only 10 seconds each.", "multiplier":1, "question_time":10},
    {"id":"streak_frenzy", "name":"🔥 STREAK FRENZY", "description":"Streak bonuses are doubled this battle.", "multiplier":1, "question_time":QUESTION_TIME},
    {"id":"accuracy_boost", "name":"🎯 ACCURACY BOOST", "description":"Every correct answer gets +2 bonus XP.", "multiplier":1, "question_time":QUESTION_TIME},
    {"id":"comeback", "name":"🚀 COMEBACK ROUND", "description":"Players outside 1st place get +2 bonus XP for each correct answer.", "multiplier":1, "question_time":QUESTION_TIME}
]

def choose_tournament_surprise(used_ids=None, final_battle=False):
    """Fresh surprise every tournament battle; Comeback only on the final battle."""
    if final_battle:
        return next(x for x in TOURNAMENT_SURPRISES if x["id"] == "comeback").copy()
    used_ids = set(used_ids or [])
    pool = [x for x in TOURNAMENT_SURPRISES if x["id"] != "comeback"]
    available = [x for x in pool if x["id"] not in used_ids]
    if not available:
        available = pool[:]
    return random.choice(available).copy()

@app.route("/api/create_room", methods=["POST"])
def create_room():
    data = request.get_json() or {}
    name = clean_name(data.get("name"))
    mode = str(data.get("mode", "mixed")).lower()
    battle_mode = str(data.get("battle_mode", "classic")).lower()
    selections = data.get("selections", [])
    if not isinstance(selections, list):
        selections = []
    
    if not name:
        return jsonify(success=False, message="Please login first.")
    with lock:
        if name not in players:
            return jsonify(success=False, message="Account not found. Please login.")
    if mode not in {"mixed", "halogen", "fluids"}:
        mode = "mixed"
    if battle_mode not in {"classic", "sudden_death", "streak", "tournament"}:
        battle_mode = "classic"
        
    try:
        amount = int(data.get("amount", 10))
    except Exception:
        amount = 10
        
    q_time = QUESTION_TIME
    # Tournament mode is a session of multiple battles with a random surprise each battle.
    if battle_mode == "tournament":
        session_battles = 3
    try:
        session_battles = max(1, min(5, int(data.get("session_battles", 1))))
    except Exception:
        session_battles = 1

    with lock:
        code = generate_code()
        if selections:
            qs, subject, topic = choose_questions_from_selection(selections, amount, battle_mode)
        else:
            qs, subject, topic = choose_questions(mode, amount, battle_mode)
        if not qs:
            return jsonify(success=False, message="No questions found for the selected topics.")
        rooms[code] = {
            "code": code,
            "host": name,
            "players": [make_player(name)],
            "status": "waiting",
            "question_index": 0,
            "questions": qs,
            "question_started": 0,
            "dare": None,
            "dare_player": None,
            "subject": subject,
            "topic": topic,
            "selections": selections,
            "battle_mode": battle_mode,
            "question_time": q_time,
            "created": time.time(),
            "chat": [{"name": "StudyBattle", "text": f"Room created by {name} 👋", "time": time.time(), "system": True}],
            "session_battles": session_battles, "session_battle": 1, "session_scores": {},
            "session_stats": {},
            "battle_awards": [], "session_special_awards": [], "session_finished": False, "session_champion": None,
            "session_last_place": None,
            "intro_duration": 10,
            "surprise_history": [],
            "surprise": None
        }
    return jsonify(success=True, code=code, amount=len(qs), subject=subject, topic=topic, session_battles=session_battles)

@app.route("/api/join_room", methods=["POST"])
def join_room():
    data = request.get_json() or {}
    code = str(data.get("code", "")).strip().upper()
    name = clean_name(data.get("name"))
    if not name or not code:
        return jsonify(success=False, message="Login and enter a room code.")
    with lock:
        if name not in players:
            return jsonify(success=False, message="Account not found. Please login.")
        room = rooms.get(code)
        if not room:
            return jsonify(success=False, message="Room not found.")
        if room["status"] != "waiting":
            return jsonify(success=False, message="Battle already started.")
        if len(room["players"]) >= MAX_PLAYERS:
            return jsonify(success=False, message="Room is full.")
        if any(p["name"].lower() == name.lower() for p in room["players"]):
            return jsonify(success=False, message="Name already used.")
        room["players"].append(make_player(name))
        room.setdefault("chat", []).append({"name": "StudyBattle", "text": f"{name} joined the room! 👋", "time": time.time(), "system": True})
        room["chat"] = room["chat"][-100:]
    return jsonify(success=True)

@app.route("/api/cancel_room", methods=["POST"])
def cancel_room():
    data = request.get_json() or {}
    code = str(data.get("code", "")).strip().upper()
    name = clean_name(data.get("name"))
    with lock:
        room = rooms.get(code)
        if not room:
            return jsonify(success=False, message="Room not found.")
        if room["host"].lower() != name.lower():
            return jsonify(success=False, message="Only the host can cancel the room.")
        rooms.pop(code, None)
    return jsonify(success=True)

@app.route("/api/start_room", methods=["POST"])
def start_room():
    data = request.get_json() or {}
    code = str(data.get("code", "")).strip().upper()
    name = clean_name(data.get("name"))
    with lock:
        room = rooms.get(code)
        if not room:
            return jsonify(success=False, message="Room not found.")
        if room["host"].lower() != name.lower():
            return jsonify(success=False, message="Only the host can start the battle.")
        if len(room["players"]) < MIN_PLAYERS:
            return jsonify(success=False, message="Need at least 2 players.")
        if room.get("status") == "finished" and room.get("session_finished"):
            return jsonify(success=False, message="This session is already complete.")
        if room.get("status") == "finished":
            room["session_battle"] = room.get("session_battle", 1) + 1
            if room["session_battle"] > room.get("session_battles", 1):
                room["session_finished"] = True
                return jsonify(success=False, message="Session complete.")
            if room.get("selections"):
                qs, subject, topic = choose_questions_from_selection(room["selections"], len(room["questions"]), room.get("battle_mode", "classic"))
            else:
                qs, subject, topic = choose_questions("mixed", len(room["questions"]), room.get("battle_mode", "classic"))
            room["questions"] = qs
            room["subject"], room["topic"] = subject, topic
            room["dare"] = None; room["dare_player"] = None; room["battle_awards"] = []
            for p in room["players"]:
                p.update({"score":0,"correct":0,"answered":0,"answer_index":-1,"current_answer":None,"streak":0,"best_streak":0,"elimination_warning":False,"eliminated":False,"max_speed_bonus":0})
        # Every tournament battle gets a fresh surprise. Final battle is always Comeback Round.
        if room.get("battle_mode") == "tournament":
            used = room.get("surprise_history", [])
            battle_no = room.get("session_battle", 1)
            total_battles = room.get("session_battles", 3)
            is_final_battle = battle_no >= total_battles
            room["surprise"] = choose_tournament_surprise(used, final_battle=is_final_battle)
            room["surprise_history"] = used + [room["surprise"].get("id")]
            room["question_time"] = room["surprise"].get("question_time", QUESTION_TIME)
        else:
            room["surprise"] = None
            room["question_time"] = QUESTION_TIME
        # Synchronized cinematic battle intro before each session battle.
        room["status"] = "intro"
        room["question_index"] = 0
        room["intro_started"] = time.time()
        room["question_started"] = 0
    return jsonify(success=True)

@app.route("/api/chat", methods=["POST"])
def send_chat():
    data = request.get_json() or {}
    code = str(data.get("code", "")).strip().upper()
    name = clean_name(data.get("name"))
    text = str(data.get("text", "")).strip()
    if not code or not name:
        return jsonify(success=False, message="Room and player are required.")
    if not text:
        return jsonify(success=False, message="Type a message first.")
    if len(text) > 240:
        return jsonify(success=False, message="Message is too long. Keep it under 240 characters.")
    with lock:
        room = rooms.get(code)
        if not room:
            return jsonify(success=False, message="Room not found.")
        if not any(p["name"].lower() == name.lower() for p in room["players"]):
            return jsonify(success=False, message="You are not in this room.")
        now = time.time()
        recent = [m for m in room.get("chat", []) if m.get("name", "").lower() == name.lower() and now - m.get("time", 0) < 8]
        if len(recent) >= 5:
            return jsonify(success=False, message="Slow down a little — chat is rate limited.")
        # Strip control characters; HTML escaping is also applied client-side.
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
        room.setdefault("chat", []).append({"name": name, "text": text, "time": now, "system": False})
        room["chat"] = room["chat"][-100:]
    return jsonify(success=True)


@app.route("/api/room")
def api_room():
    code = request.args.get("code", "").strip().upper()
    with lock:
        room = rooms.get(code)
        if not room:
            return jsonify(success=False, message="Room not found.")
        if room["status"] == "intro":
            if time.time() - room.get("intro_started", time.time()) >= room.get("intro_duration", 10):
                room["status"] = "playing"
                room["question_started"] = time.time()
                for p in room["players"]:
                    p["answer_index"] = -1
                    p["current_answer"] = None
        if room["status"] == "playing":
            active_players = [p for p in room["players"] if not p.get("eliminated", False)]
            everyone = all(p["answer_index"] == room["question_index"] for p in active_players)
            timeout = time.time() - room["question_started"] >= room.get("question_time", QUESTION_TIME)
            if everyone or timeout:
                advance_room(room)
        return jsonify(success=True, room=public_room(room))

@app.route("/api/answer_room", methods=["POST"])
def answer_room():
    data = request.get_json() or {}
    code = str(data.get("code", "")).strip().upper()
    name = clean_name(data.get("name"))
    try:
        answer = int(data.get("answer", -1))
        qi = int(data.get("question_index", -1))
    except Exception:
        return jsonify(success=False, message="Invalid answer.")
        
    with lock:
        room = rooms.get(code)
        if not room:
            return jsonify(success=False, message="Room not found.")
        if room["status"] != "playing":
            return jsonify(success=False, message="Battle is not active.")
        if qi != room["question_index"]:
            return jsonify(success=False, message="Question changed.")
        if answer < 0 or answer > 3:
            return jsonify(success=False, message="Invalid option.")
            
        q_time = room.get("question_time", QUESTION_TIME)
        elapsed = time.time() - room["question_started"]
        if elapsed > q_time:
            advance_room(room)
            return jsonify(success=False, message="Time expired.")
            
        player = next((p for p in room["players"] if p["name"].lower() == name.lower()), None)
        if not player:
            return jsonify(success=False, message="Player not found.")
        if player.get("eliminated", False):
            return jsonify(success=False, message="You are eliminated from answering!")
        if player["answer_index"] == qi:
            return jsonify(success=False, message="Already answered.")
            
        q = room["questions"][qi]
        player["answer_index"] = qi
        player["current_answer"] = answer
        player["answered"] += 1
        correct = (answer == q["answer"])
        
        gained_points = 0
        speed_bonus = 0
        streak_bonus = 0
        
        is_final = (qi == len(room["questions"]) - 1)
        base_multiplier = 3 if is_final else 1
        surprise = room.get("surprise") or {}
        if room.get("battle_mode") == "tournament":
            if surprise.get("id") == "double_xp":
                base_multiplier *= 2

        if correct:
            player["correct"] += 1
            player["streak"] += 1
            player["best_streak"] = max(player["best_streak"], player["streak"])
            
            # Speed Bonus Calculation
            if elapsed <= 3.0:
                speed_bonus = 3
            elif elapsed <= 7.0:
                speed_bonus = 2
            elif elapsed <= 15.0:
                speed_bonus = 1
                
            # Streak Bonus Calculation
            if room.get("battle_mode") == "streak":
                streak_bonus = player["streak"] * 2
            elif player["streak"] >= 5:
                streak_bonus = 3
            elif player["streak"] >= 3:
                streak_bonus = 2
            elif player["streak"] >= 2:
                streak_bonus = 1
                
            if room.get("battle_mode") == "tournament" and surprise.get("id") == "streak_frenzy":
                streak_bonus *= 2
            gained_points = (BASE_POINTS + speed_bonus + streak_bonus) * base_multiplier
            if room.get("battle_mode") == "tournament" and surprise.get("id") == "accuracy_boost":
                gained_points += 2
            if room.get("battle_mode") == "tournament" and surprise.get("id") == "comeback":
                live_scores = sorted([x.get("score", 0) for x in room["players"]], reverse=True)
                if live_scores and player.get("score", 0) < live_scores[0]:
                    gained_points += 2
            player["score"] += gained_points
            player["max_speed_bonus"] = max(player.get("max_speed_bonus", 0), speed_bonus)
        else:
            player["streak"] = 0
            if room.get("battle_mode") == "sudden_death":
                player["eliminated"] = True
                
        return jsonify(
            success=True, 
            correct=correct, 
            score=player["score"], 
            points=gained_points,
            speed_bonus=speed_bonus,
            streak=player["streak"],
            correct_answer_index=q["answer"],
            correct_answer=q["options"][q["answer"]]
        )

@app.route("/api/dashboard")
def dashboard():
    with lock:
        ranking = []
        for n, d in players.items():
            # Testing accounts remain usable, but do not affect the public Hall of Fame.
            if str(n).strip().lower() in HALL_OF_FAME_HIDDEN_NAMES:
                continue
            refresh_level(d)
            safe = {"name": n, **d}
            safe.pop("password_hash", None)
            ranking.append(safe)
        ranking.sort(key=lambda x: (x.get("wins", 0), x.get("win_streak", 0), x.get("xp", 0)), reverse=True)
        return jsonify(success=True, players=ranking)

load_uploaded_questions()

def room_cleanup():
    while True:
        time.sleep(60)
        now = time.time()
        with lock:
            for code, room in list(rooms.items()):
                if now - room.get("created", now) > 3600:
                    rooms.pop(code, None)

HTML = r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>StudyBattle • Smart Study Battles</title><style>
*{box-sizing:border-box}body{margin:0;min-height:100vh;font-family:Inter,Arial,sans-serif;background:radial-gradient(circle at top,#18244b,#090d1d 48%,#050711);color:#f8fafc}.container{max-width:760px;margin:auto;padding:14px}.hidden{display:none!important}.screen{animation:in .25s ease}@keyframes in{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}.brand{text-align:center;padding:16px 0 8px}.logo{font-size:40px;font-weight:1000;letter-spacing:-2px}.logo span{color:#a78bfa}.tag{color:#94a3b8;margin-top:4px}.card{background:rgba(15,23,42,.87);border:1px solid #1e293b;border-radius:22px;padding:19px;margin-top:13px;box-shadow:0 18px 55px #0005;backdrop-filter:blur(12px)}.title{font-size:24px;font-weight:900}.muted{color:#94a3b8}input,select{width:100%;padding:15px;margin-top:10px;border-radius:13px;border:1px solid #334155;background:#0b1120;color:white;font-size:16px;outline:none}input:focus,select:focus{border-color:#38bdf8}button{width:100%;padding:15px;margin-top:10px;border:0;border-radius:13px;background:linear-gradient(135deg,#7c3aed,#38bdf8);color:white;font-weight:900;font-size:16px;cursor:pointer}button:disabled{opacity:.6}.secondary{background:#1e293b}.danger-btn{background:linear-gradient(135deg,#e11d48,#9f1239)}.modegrid{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin-top:10px}.mode{padding:13px 12px;text-align:left;border:1px solid #334155;border-radius:15px;background:linear-gradient(180deg,#111827,#0b1120);font-weight:900;cursor:pointer;transition:.18s;min-height:78px}.mode:hover{transform:translateY(-1px);border-color:#475569}.mode.active{border-color:#38bdf8;background:linear-gradient(135deg,#172554,#0e7490);box-shadow:0 0 0 1px #38bdf855,0 8px 24px #0005}.mode .modeicon{font-size:22px;display:block;margin-bottom:4px}.mode .modename{display:block;font-size:14px}.mode .modesub{display:block;color:#94a3b8;font-size:11px;font-weight:700;margin-top:3px}.mode.active .modesub{color:#bae6fd}.roomcode{text-align:center;font-size:40px;font-weight:1000;letter-spacing:7px;color:#a78bfa;margin:10px}.row,.rank{display:flex;align-items:center;justify-content:space-between;background:#111827;border-radius:12px;padding:12px;margin-top:7px}.score{color:#38bdf8;font-weight:900}.badge{font-size:10px;padding:4px 7px;border-radius:999px;background:#164e63;color:#67e8f9;margin-left:5px}.warning-badge{background:#881337;color:#fda4af;font-size:10px;padding:3px 6px;border-radius:6px;margin-left:6px;font-weight:bold}.battlehead{display:flex;justify-content:space-between;align-items:center}.timer{width:62px;height:62px;border-radius:50%;display:flex;align-items:center;justify-content:center;background:#111827;border:4px solid #38bdf8;font-size:23px;font-weight:1000}.timer.danger{border-color:#fb7185;color:#fb7185}.q{font-size:24px;line-height:1.35;font-weight:900;margin:8px 0 16px}.opt{text-align:left;background:#111827;border:1px solid #334155}.opt:hover{border-color:#38bdf8;background:#172554}.correct{border:2px solid #22c55e!important;background:#16653455!important}.wrong{border:2px solid #fb7185!important;background:#7f1d1d55!important}.feedback{position:fixed;z-index:9;left:50%;top:50%;transform:translate(-50%,-50%);padding:24px;min-width:240px;text-align:center;border:2px solid;border-radius:20px;background:#0f172af5;box-shadow:0 20px 70px #0009}.feedback.good{border-color:#22c55e}.feedback.bad{border-color:#fb7185}.feedback b{font-size:28px}.resulticon{text-align:center;font-size:65px}.resulttitle{text-align:center;font-size:30px;font-weight:1000}.podium .row:first-child{border:1px solid #facc15;background:#4b3b0050}.dare{padding:22px;margin-top:14px;border-radius:20px;text-align:center;background:linear-gradient(135deg,#3b0764,#701a75);border:2px solid #e879f9}.darelabel{font-size:29px;font-weight:1000}.daretext{font-size:19px;font-weight:700;line-height:1.45;margin-top:12px}.small{font-size:12px;color:#64748b;margin-top:8px}.topiccatalog{margin-top:10px}.subjectbox{background:#0b1120;border:1px solid #1e293b;border-radius:14px;padding:10px;margin-top:8px}.subjecttitle{font-weight:900;color:#38bdf8;margin-bottom:6px}.topiccheck{display:flex;align-items:center;gap:8px;padding:8px;border-radius:9px;cursor:pointer}.topiccheck:hover{background:#111827}.topiccheck input{width:auto;margin:0}.topiccheck span{font-size:14px}.pdfbox input[type=file]{border:1px dashed #38bdf8;background:#0f172a}.pdfbox button{margin-top:10px}.statsgrid{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin-bottom:12px}.statbox{background:#0b1120;border:1px solid #1e293b;border-radius:10px;padding:8px;text-align:center}.statval{font-size:16px;font-weight:900;color:#38bdf8}.statlbl{font-size:10px;color:#64748b}.chatbox{margin-top:12px}.chatmessages{height:220px;overflow-y:auto;background:#080d1a;border:1px solid #1e293b;border-radius:14px;padding:10px}.chatmsg{padding:7px 9px;margin-bottom:6px;background:#111827;border-radius:10px;word-break:break-word}.chatmsg .chatname{font-weight:900;color:#67e8f9;font-size:12px}.chatmsg .chattime{font-size:9px;color:#64748b;margin-left:6px}.chatmsg .chattext{margin-top:2px;font-size:13px;line-height:1.35}.chatform{display:flex;gap:7px;margin-top:8px}.chatform input{margin-top:0;flex:1}.chatform button{width:auto;margin-top:0;padding:12px 16px}.chat-empty{color:#64748b;text-align:center;padding:55px 8px;font-size:13px}@media(max-width:480px){.logo{font-size:34px}.q{font-size:21px}.roomcode{font-size:32px;letter-spacing:5px}.modegrid{grid-template-columns:1fr}.card{padding:16px}.statsgrid{grid-template-columns:repeat(2,1fr)}}
.session-champion-overlay{position:fixed;inset:0;z-index:220;background:radial-gradient(circle at 50% 42%,rgba(250,204,21,.2),rgba(2,6,23,.96) 58%);backdrop-filter:blur(12px);display:flex;align-items:center;justify-content:center;overflow:hidden}.session-champion-card{position:relative;width:min(94vw,620px);padding:42px 24px;text-align:center;border:3px solid #facc15;border-radius:32px;background:linear-gradient(145deg,#1e1b4b,#172554 45%,#3b0764);box-shadow:0 0 35px #facc1566,0 0 120px #facc1533,0 30px 120px #000d;animation:championBoom .8s cubic-bezier(.16,1.4,.3,1)}.champion-crown{font-size:92px;line-height:1;animation:championCrown .9s ease-in-out infinite}.champion-kicker{font-size:16px;letter-spacing:5px;font-weight:1000;color:#fde68a;margin-top:12px}.champion-heading{font-size:42px;font-weight:1000;letter-spacing:-1.5px;margin-top:8px;text-shadow:0 0 25px #facc1599}.champion-name{font-size:44px;font-weight:1000;color:#fef08a;margin-top:10px;word-break:break-word;text-shadow:0 0 30px #facc15cc}.champion-sub{font-size:18px;font-weight:900;color:#e2e8f0;margin-top:10px}.meow-badge{display:inline-block;margin-top:18px;padding:9px 16px;border-radius:999px;background:#facc1522;border:1px solid #facc1577;color:#fde68a;font-weight:1000;letter-spacing:1px}.champion-flash{position:absolute;inset:0;background:#fff7;opacity:0;pointer-events:none;animation:championFlash .45s ease-out}.champion-shockwave{position:absolute;left:50%;top:50%;width:50px;height:50px;border:4px solid #facc15;border-radius:50%;transform:translate(-50%,-50%);animation:shockwave 1.1s ease-out infinite;pointer-events:none}@keyframes championBoom{0%{opacity:0;transform:scale(.35) rotate(-2deg)}65%{transform:scale(1.05)}100%{opacity:1;transform:scale(1)}}@keyframes championCrown{0%,100%{transform:translateY(0) rotate(-3deg) scale(1)}50%{transform:translateY(-12px) rotate(3deg) scale(1.08)}}@keyframes championFlash{0%{opacity:.8}100%{opacity:0}}@keyframes shockwave{0%{width:50px;height:50px;opacity:.8}100%{width:900px;height:900px;opacity:0}}.result-actions{border-top:1px solid #1e293b}.battle-result-overlay{position:fixed;inset:0;z-index:100;background:rgba(2,6,23,.82);backdrop-filter:blur(8px);display:flex;align-items:center;justify-content:center;overflow:hidden}.battle-result-card{position:relative;width:min(92vw,520px);padding:34px 24px;text-align:center;border:2px solid #facc15;border-radius:28px;background:linear-gradient(145deg,#111827,#172554 55%,#3b0764);box-shadow:0 0 0 1px #facc1533,0 25px 100px #000b;animation:winnerPop .65s cubic-bezier(.2,1.5,.4,1)}.battle-result-card .trophy{font-size:76px;animation:trophyBounce 1s ease-in-out infinite}.battle-result-card .congrats{font-size:38px;font-weight:1000;letter-spacing:-1px;margin-top:5px}.battle-result-card .winner-label{font-size:13px;color:#cbd5e1;margin-top:8px;text-transform:uppercase;letter-spacing:3px;font-weight:900}.battle-result-card .winner-name{font-size:34px;font-weight:1000;color:#fde68a;margin-top:4px;text-shadow:0 0 25px #facc15aa;word-break:break-word}.battle-result-card .champion-line{font-size:18px;font-weight:800;margin-top:12px}.confetti-piece{position:absolute;top:-20px;width:9px;height:16px;border-radius:2px;animation:confettiFall 2.8s linear forwards;pointer-events:none}.sparkle{position:absolute;font-size:24px;animation:sparkleFloat 1.8s ease-out forwards;pointer-events:none}@keyframes winnerPop{0%{transform:scale(.55) translateY(30px);opacity:0}70%{transform:scale(1.04)}100%{transform:scale(1);opacity:1}}@keyframes trophyBounce{0%,100%{transform:translateY(0) rotate(-2deg)}50%{transform:translateY(-9px) rotate(2deg)}}@keyframes confettiFall{0%{transform:translateY(-10px) rotate(0deg);opacity:1}100%{transform:translateY(110vh) rotate(720deg);opacity:0}}@keyframes sparkleFloat{0%{transform:scale(.2) translateY(20px);opacity:0}35%{opacity:1}100%{transform:scale(1.2) translateY(-80px);opacity:0}}.correct-answer-hint{margin-top:10px;padding:10px 12px;border-radius:12px;background:#14532d88;border:1px solid #22c55e;color:#bbf7d0;font-weight:900}.wrong-choice{border-color:#fb7185!important;background:#7f1d1d66!important}.right-choice{border-color:#22c55e!important;background:#16653466!important}.popup-back-btn{position:relative;z-index:3;margin-top:22px;background:linear-gradient(135deg,#334155,#1e293b);border:1px solid #64748b}.popup-back-btn:hover{transform:translateY(-1px);filter:brightness(1.08)}.battle-moment{position:fixed;z-index:80;left:50%;top:24%;transform:translate(-50%,-50%) scale(.85);padding:13px 20px;border-radius:18px;background:rgba(15,23,42,.96);border:1px solid #38bdf8;box-shadow:0 15px 55px #0009;font-weight:1000;font-size:20px;animation:momentPop 1.35s ease forwards;pointer-events:none}@keyframes momentPop{0%{opacity:0;transform:translate(-50%,-30%) scale(.75)}15%{opacity:1;transform:translate(-50%,-50%) scale(1.05)}75%{opacity:1}100%{opacity:0;transform:translate(-50%,-80%) scale(1)}}
.battle-intro-card{width:min(92vw,560px);min-height:70vh;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:35px 22px;border:2px solid #38bdf8;border-radius:30px;background:radial-gradient(circle at 50% 30%,#172554,#0b1120 65%);box-shadow:0 0 60px #38bdf844;animation:introCard .7s ease-out}.intro-swords{font-size:76px;animation:introSword 1.2s ease-in-out infinite}.intro-kicker{font-size:14px;letter-spacing:6px;font-weight:1000;color:#67e8f9;margin-top:12px}.intro-topic{font-size:32px;font-weight:1000;margin-top:10px;max-width:90%}.intro-mode{font-size:17px;font-weight:900;color:#cbd5e1;margin-top:8px}.intro-players{font-size:15px;color:#94a3b8;margin-top:7px}.intro-countdown-wrap{margin-top:30px;width:150px;height:150px;border-radius:50%;display:flex;align-items:center;justify-content:center;border:3px solid #38bdf8;box-shadow:0 0 35px #38bdf866}.intro-countdown{font-size:76px;font-weight:1000;color:#f8fafc;animation:introCount .8s ease-in-out}.intro-status{font-size:16px;font-weight:1000;letter-spacing:2px;color:#facc15;margin-top:25px}@keyframes introCard{from{opacity:0;transform:scale(.82) translateY(25px)}to{opacity:1;transform:scale(1) translateY(0)}}@keyframes introSword{0%,100%{transform:translateY(0) rotate(-3deg)}50%{transform:translateY(-8px) rotate(3deg)}}@keyframes introCount{0%{transform:scale(1.3);opacity:.4}100%{transform:scale(1);opacity:1}}.tournament-next-note{margin-top:12px;padding:12px 14px;border-radius:14px;background:#0b1120;border:1px solid #334155;color:#cbd5e1;font-size:13px;font-weight:800}.session-champion-row{border:1px solid #facc15!important;background:linear-gradient(135deg,#3b2f0555,#111827)!important}.battle-intro-card{box-shadow:0 24px 90px #0008!important}.result-title{letter-spacing:-.5px}.card{box-shadow:0 12px 38px #0004;backdrop-filter:blur(10px)}button{transition:transform .15s ease,filter .15s ease,box-shadow .15s ease}button:hover{filter:brightness(1.06);transform:translateY(-1px);box-shadow:0 8px 22px #0004}.mode{box-shadow:0 6px 18px #0003}.mode.active{box-shadow:0 0 0 1px #38bdf855,0 10px 28px #0005}.row{border:1px solid transparent}.row:hover{border-color:#334155}.battle-result-card{box-shadow:0 25px 90px #000a}.session-winner-card{border:1px solid #facc15;background:linear-gradient(135deg,#2b2206,#0f172a);box-shadow:0 14px 45px #facc1530}.session-winner-card .session-champion-row{border:1px solid #facc15!important;background:linear-gradient(135deg,#3b2f0555,#111827)!important}.specialAwardsSection{}
/* V8 professional UI */
:root{--bg:#130f22;--panel:#181227;--panel2:#1e1832;--line:#332a52;--text:#f8fafc;--muted:#a396c4;--accent:#a78bfa;--accent2:#38bdf8;--danger:#fb7185;--success:#34d399}
body{background:radial-gradient(900px 500px at 50% -120px,#3b2f66 0%,#1e1a2e 45%,#100c1c 100%);letter-spacing:-.01em}.container{max-width:820px;padding:18px}.brand{padding:22px 0 12px}.logo{font-size:38px}.tag{font-size:14px}.card{background:rgba(10,17,31,.88);border:1px solid rgba(96,125,164,.2);border-radius:24px;padding:22px;box-shadow:0 18px 60px rgba(0,0,0,.28)}
button{min-height:52px;border-radius:14px;box-shadow:none}button:active{transform:translateY(1px) scale(.99)}button:focus-visible,.mode:focus-visible{outline:2px solid var(--accent);outline-offset:3px}.secondary{background:#182338;border:1px solid #2b3b58}.danger-btn{background:linear-gradient(135deg,#be123c,#9f1239)}input,select{border-radius:14px;border:1px solid #293a57;background:#080f1e;min-height:52px}input::placeholder{color:#65758f}.section-label{font-size:11px;font-weight:1000;letter-spacing:1.8px;color:#7083a1;margin:18px 0 8px}.section-head{display:flex;align-items:flex-end;justify-content:space-between;gap:12px;margin-top:18px}.section-head .section-label{margin:0}.refresh-btn{width:auto;min-height:40px;padding:8px 13px;margin:0;background:#111b2d;border:1px solid #2b3b58;font-size:13px}.pdfbox{margin-top:8px;padding:18px;border:1px solid #24527a;border-radius:22px;background:linear-gradient(145deg,rgba(13,35,61,.95),rgba(10,18,33,.95));box-shadow:0 16px 45px rgba(0,0,0,.25)}.pdf-top{display:flex;justify-content:space-between;align-items:flex-start;gap:12px}.pdf-title{font-size:21px;font-weight:1000}.pdf-subtitle{font-size:13px;color:#91a2ba;margin-top:5px;line-height:1.4}.pdf-badge{font-size:11px;font-weight:1000;letter-spacing:1px;padding:7px 9px;border-radius:9px;background:#0ea5e91c;color:#67e8f9;border:1px solid #0ea5e955}.pdf-grid{display:grid;grid-template-columns:1fr 1fr;gap:9px;margin-top:14px}.pdf-grid input{margin-top:0}.file-drop{display:flex;align-items:center;gap:12px;margin-top:9px;padding:14px;border:1px dashed #3b82f6;background:#091426;border-radius:15px;cursor:pointer}.file-drop:hover{border-color:#67e8f9;background:#0c1a2f}.file-icon{width:36px;height:36px;display:grid;place-items:center;border-radius:10px;background:#0ea5e91a;color:#67e8f9;font-size:22px}.file-drop b{display:block;font-size:14px}.file-drop small{display:block;color:#71839e;margin-top:3px}.visually-hidden{position:absolute!important;width:1px!important;height:1px!important;padding:0!important;margin:-1px!important;overflow:hidden!important;clip:rect(0,0,0,0)!important;white-space:nowrap!important;border:0!important}.pdfbox button{margin-top:9px}.status-line{min-height:18px;color:#9fb1c9;font-size:12px;margin-top:8px}.subjectbox{padding:12px;background:rgba(8,15,28,.82);border:1px solid #1e2c44;border-radius:17px;margin-top:9px}.subjecttitle{display:flex;justify-content:space-between;align-items:center;color:#e5f4ff;font-size:14px;padding:3px 3px 7px}.set-count{font-size:11px;color:#71839e;font-weight:800}.studyset-row{display:flex;align-items:center;gap:8px;border-top:1px solid #17243a}.topiccheck{flex:1;min-width:0;padding:12px 7px;margin:0}.topiccheck span{display:flex;flex-direction:column;gap:3px}.topiccheck span b{font-size:14px;color:#e8eef7}.topiccheck span small{font-size:11px;color:#71839e}.topiccheck input{accent-color:#38bdf8}.icon-delete{width:42px;min-height:40px;height:40px;padding:0;margin:0;background:#351522;border:1px solid #64243a;color:#fda4af;font-size:16px}.icon-delete:hover{background:#4a1b2b;box-shadow:none}.empty-state{display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:30px 18px;border:1px dashed #263750;border-radius:18px;background:#09111f;color:#8fa0b8;gap:6px}.empty-state b{color:#dbe7f4;font-size:14px}.empty-state span{font-size:12px}.empty-icon{font-size:28px;margin-bottom:2px}.mode{border-radius:17px;min-height:92px}.statsgrid{gap:9px}.statbox{border-radius:14px}.row{border-radius:14px;padding:14px}.toast{position:fixed;left:50%;bottom:22px;transform:translateX(-50%);z-index:500;max-width:min(92vw,520px);padding:13px 16px;border-radius:14px;background:#111c30;border:1px solid #334766;box-shadow:0 18px 55px #0009;color:#eef6ff;font-weight:800;font-size:13px;animation:toastIn .22s ease;backdrop-filter:blur(12px)}.toast.success{border-color:#238b68}.toast.error{border-color:#a52b4c}.toast.out{opacity:0;transform:translate(-50%,8px);transition:.2s}@keyframes toastIn{from{opacity:0;transform:translate(-50%,10px)}to{opacity:1;transform:translate(-50%,0)}}@media(max-width:560px){.container{padding:12px}.pdf-grid{grid-template-columns:1fr}.pdfbox{padding:15px}.section-head{align-items:center}.refresh-btn{min-height:38px}.card{padding:17px;border-radius:20px}.logo{font-size:33px}}
:root{--bg:#070b14;--surface:#0d1422;--surface2:#111b2d;--line:#22304a;--text:#f8fafc;--muted:#91a0b8;--primary:#5b8cff;--cyan:#22d3ee;--good:#34d399;--danger:#fb7185;--shadow:0 24px 80px rgba(0,0,0,.38)}
html{background:var(--bg);scroll-behavior:smooth}body{background:radial-gradient(900px 500px at 50% -120px,rgba(91,140,255,.20),transparent 65%),linear-gradient(180deg,#080d18 0%,#050811 100%);font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;letter-spacing:-.01em}.container{max-width:920px;padding:20px 16px 48px}.brand{padding:18px 0 14px}.logo{font-size:34px;letter-spacing:-1.8px}.logo span{background:linear-gradient(90deg,#7dd3fc,#60a5fa,#a78bfa);-webkit-background-clip:text;background-clip:text;color:transparent}.tag{font-size:13px;color:#8392aa}.card{border:1px solid rgba(148,163,184,.14);background:linear-gradient(180deg,rgba(17,27,45,.92),rgba(10,16,28,.94));border-radius:24px;padding:22px;margin-top:14px;box-shadow:var(--shadow);backdrop-filter:blur(16px)}.title{font-size:25px;letter-spacing:-.6px}.muted,.small{color:var(--muted)}input,select{height:52px;margin-top:9px;border-radius:14px;border:1px solid #273650;background:#080f1d;color:#f8fafc;padding:0 15px;box-shadow:inset 0 1px 0 rgba(255,255,255,.03);transition:.18s}.pdf-grid input{height:52px}input::placeholder{color:#64748b}input:focus,select:focus{border-color:#5b8cff;box-shadow:0 0 0 4px rgba(91,140,255,.12);outline:none}button{min-height:52px;margin-top:10px;border-radius:14px;background:linear-gradient(135deg,#4f7df3,#22b8d8);box-shadow:0 10px 26px rgba(34,184,216,.14);transition:transform .15s,filter .15s,box-shadow .15s}button:hover:not(:disabled){transform:translateY(-1px);filter:brightness(1.06);box-shadow:0 14px 32px rgba(34,184,216,.18)}button:active:not(:disabled){transform:translateY(0)}button.secondary{background:#172236;border:1px solid #2a3a56;box-shadow:none}.danger-btn{background:linear-gradient(135deg,#be314d,#8f1835)}.section-label{font-size:11px;letter-spacing:2.1px;color:#7f91ae;font-weight:900;margin-top:24px}.pdfbox{margin-top:10px;padding:20px;border:1px solid rgba(96,165,250,.28);border-radius:22px;background:linear-gradient(145deg,rgba(15,36,64,.92),rgba(8,18,33,.96))}.pdf-top{gap:14px}.pdf-title{font-size:23px;font-weight:950;letter-spacing:-.5px}.pdf-subtitle{font-size:14px;line-height:1.55;color:#8ea1bb;margin-top:5px}.pdf-badge{border-radius:999px;padding:8px 11px;font-size:11px;font-weight:950;letter-spacing:1.2px;color:#67e8f9;border:1px solid #155e75;background:#083344}.file-drop{min-height:90px;border:1px dashed #4d7ff0!important;border-radius:18px!important;background:rgba(8,15,29,.72)!important;padding:17px!important;transition:.18s!important}.file-drop:hover{background:rgba(25,45,78,.7)!important;border-color:#67e8f9!important}.file-icon{width:46px!important;height:46px!important;border-radius:13px!important;background:#0b2a44!important;color:#67e8f9!important}.file-drop small{color:#71829c!important}.status-line{min-height:22px;margin-top:10px;color:#8ea1bb;font-size:13px;line-height:1.45}.pdf-progress-wrap{margin-top:12px;padding:12px 13px;border:1px solid #223553;background:#08111f;border-radius:15px}.pdf-progress-top,.pdf-progress-meta{display:flex;justify-content:space-between;gap:10px;align-items:center;font-size:11px;color:#8ea1bb}.pdf-progress-top strong{color:#67e8f9;font-size:12px}.pdf-progress{height:9px;margin:8px 0;border-radius:99px;background:#16233a;overflow:hidden}.pdf-progress>div{height:100%;width:0;border-radius:99px;background:linear-gradient(90deg,#4f7df3,#22b8d8);transition:width .35s ease}.pdf-progress-meta{font-size:10px;color:#61738e}.section-head{display:flex;align-items:flex-end;justify-content:space-between;gap:12px;margin-top:26px}.refresh-btn{width:auto;min-height:44px;padding:0 15px;margin:0;background:#121c2d;border:1px solid #2b3b57;box-shadow:none}.subjectbox{border:1px solid #1d2a40;background:#0a1120;border-radius:18px;padding:8px;margin-top:10px}.subjecttitle{padding:9px 10px 5px;color:#8ddff4;display:flex;justify-content:space-between;gap:10px}.set-count{color:#64748b;font-size:11px}.studyset-row{display:flex;align-items:center;gap:8px;border-top:1px solid #172339}.topiccheck{flex:1;padding:13px 10px}.topiccheck span{display:flex;flex-direction:column;gap:3px}.topiccheck small{font-size:11px;color:#667792}.topiccheck input{height:auto;accent-color:#5b8cff}.icon-delete{width:42px!important;min-height:42px!important;height:42px!important;margin:0 5px 0 0!important;padding:0!important;background:#1b1420!important;border:1px solid #442436!important;color:#fb7185!important;box-shadow:none!important}.modegrid{gap:12px}.mode{min-height:92px;border:1px solid #263650;background:linear-gradient(180deg,#111a2a,#0b1220);border-radius:18px;padding:15px;box-shadow:none}.mode.active{border-color:#5b8cff;background:linear-gradient(145deg,#17264a,#0e3444);box-shadow:0 0 0 3px rgba(91,140,255,.08)}.mode .modeicon{font-size:20px}.mode .modename{font-size:15px}.mode .modesub{font-size:11px;color:#7789a4}.statsgrid{gap:10px}.statbox{border:1px solid #1e2b42;background:#0a1120;border-radius:15px;padding:12px}.statval{font-size:20px;color:#8ddff4}.row,.rank{border:1px solid #1b2940;background:#0b1220;border-radius:14px;padding:13px;margin-top:8px}.score{color:#8ddff4}.roomcode{font-size:42px;letter-spacing:8px;padding:10px 0}.battlehead{position:sticky;top:0;z-index:5;padding:8px 0 12px;background:linear-gradient(180deg,#070b14 70%,transparent)}.timer{width:58px;height:58px;border:3px solid #5b8cff;background:#0c1628;box-shadow:0 0 0 5px rgba(91,140,255,.08);font-size:20px}.q{font-size:25px;line-height:1.42;letter-spacing:-.4px}.opt{min-height:58px;margin-top:9px;background:#0c1525;border:1px solid #263650;text-align:left}.opt:hover{background:#13213a}.correct,.right-choice{background:rgba(16,101,72,.3)!important}.wrong,.wrong-choice{background:rgba(127,29,55,.28)!important}.empty-state{border:1px dashed #263650!important;background:#0a1120!important;border-radius:18px!important;padding:35px 20px!important;color:#8a9ab2}.chatmessages{background:#070d18;border-color:#1c2940}.chatmsg{background:#0e1727;border:1px solid #18263c}.chatname{color:#8ddff4!important}.dare{background:linear-gradient(145deg,#28164b,#17264b);border-color:#a855f7}.battle-result-card,.session-champion-card{border-color:#7c9cff;box-shadow:0 25px 100px rgba(0,0,0,.65),0 0 60px rgba(91,140,255,.15)}.popup-back-btn{max-width:260px;margin-left:auto;margin-right:auto}.result-actions{background:transparent;border-top:0;padding-top:0}@media(max-width:600px){.container{padding:12px 11px 34px}.card{padding:17px;border-radius:20px}.logo{font-size:30px}.title{font-size:22px}.q{font-size:21px}.roomcode{font-size:34px;letter-spacing:6px}.pdfbox{padding:16px}.pdf-top{align-items:flex-start}.section-head{align-items:center}.section-head .small{font-size:12px}.modegrid{grid-template-columns:1fr}.statsgrid{grid-template-columns:repeat(2,1fr)}}


:root{--bg:#070b13;--panel:#0d1422;--panel2:#111b2d;--line:#22304a;--text:#f7f9fc;--muted:#8796ae;--blue:#6c8cff;--cyan:#36d9e8;--violet:#9b8cff;--green:#42d7a1;--danger:#ff718b}
body{background:radial-gradient(700px 360px at 50% -90px,rgba(108,140,255,.18),transparent 68%),radial-gradient(500px 300px at 100% 30%,rgba(54,217,232,.07),transparent 70%),#070b13;color:var(--text)}
.container{max-width:980px;padding:18px 18px 60px}.brand{text-align:left;display:flex;align-items:end;justify-content:space-between;gap:18px;padding:18px 2px 20px}.brand .tag{text-align:right}.logo{font-size:32px;letter-spacing:-1.6px}.tag{font-size:12px;letter-spacing:.2px;color:#7f8da5}
.card{background:linear-gradient(180deg,rgba(16,25,41,.94),rgba(10,16,27,.96));border:1px solid rgba(148,163,184,.13);border-radius:26px;padding:24px;box-shadow:0 24px 80px rgba(0,0,0,.32)}
.title{font-size:27px;letter-spacing:-.8px}.section-label{margin-top:28px;color:#7889a4;font-size:10px;letter-spacing:2.4px}.pdfbox{position:relative;padding:22px;border-radius:24px;border:1px solid rgba(108,140,255,.30);background:linear-gradient(145deg,rgba(17,35,63,.88),rgba(8,15,27,.98));overflow:hidden}.pdfbox:before{content:"";position:absolute;inset:0;background:linear-gradient(115deg,rgba(108,140,255,.08),transparent 38%,rgba(54,217,232,.05));pointer-events:none}.pdf-top{position:relative;z-index:1}.pdf-title{font-size:24px}.pdf-subtitle{max-width:600px;color:#93a2ba}.pdf-badge{display:none}.quality-pill{margin-left:auto;padding:7px 10px;border-radius:999px;border:1px solid rgba(54,217,232,.25);background:rgba(54,217,232,.07);color:#74e7f0;font-size:9px;font-weight:900;letter-spacing:1.3px;white-space:nowrap}
.pdf-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:15px}.file-drop{position:relative;z-index:1;min-height:96px!important;margin-top:12px!important;border:1px dashed #426bd0!important;background:rgba(5,12,23,.58)!important}.file-drop:hover{transform:translateY(-1px);box-shadow:0 10px 35px rgba(58,110,255,.12)}
button{font-weight:850;letter-spacing:-.1px}.pdfbox button{position:relative;z-index:1}.pdf-trust{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px;color:#65758f;font-size:10px}.pdf-trust span{padding:5px 8px;border-radius:999px;background:#0a1321;border:1px solid #17253a}.section-head{margin-top:30px}.subjectbox{background:rgba(8,14,24,.78);border:1px solid #1b2940;border-radius:20px;padding:8px}.subjecttitle{font-size:13px;padding:10px 11px;color:#91dff1}.studyset-row{border-top:1px solid #172237}.topiccheck{padding:14px 11px}.topiccheck span b{font-size:14px}.topiccheck small{font-size:10px;color:#6f8099}.icon-delete{border-radius:12px!important}
.modegrid{grid-template-columns:repeat(4,1fr);gap:10px}.mode{min-height:110px;padding:16px;border-radius:18px;background:linear-gradient(180deg,#101a2a,#0a111e);transition:.18s}.mode:hover{transform:translateY(-2px)}.mode.active{background:linear-gradient(145deg,#17244a,#0d2c3c)}
input,select{background:#080f1b;border-color:#243550}.statsgrid{gap:9px}.statbox{border-radius:16px;background:#09111f;border-color:#1b2a42}.statval{font-size:21px}.q{font-size:27px;max-width:850px}.opt{border-radius:15px;min-height:60px}.empty-state{min-height:170px;display:flex;flex-direction:column;align-items:center;justify-content:center}
@media(max-width:760px){.brand{align-items:flex-start;flex-direction:column}.brand .tag{text-align:left}.pdf-grid{grid-template-columns:1fr}.modegrid{grid-template-columns:1fr 1fr}.q{font-size:22px}.quality-pill{display:none}}
@media(max-width:480px){.container{padding:12px 11px 36px}.card{padding:17px;border-radius:21px}.modegrid{grid-template-columns:1fr}.pdfbox{padding:16px}.title{font-size:23px}}

/* StudyBattle polished navigation + Practice + You */
.app-shell{display:flex;flex-direction:column;gap:14px}.topbar{position:sticky;top:0;z-index:40;display:flex;align-items:center;justify-content:space-between;gap:12px;padding:10px 4px;background:rgba(7,11,19,.82);backdrop-filter:blur(18px);border-bottom:1px solid rgba(148,163,184,.08)}.topbar-brand{font-weight:1000;letter-spacing:-.7px;font-size:18px}.topbar-brand span{color:#7dd3fc}.avatar{width:40px;height:40px;border-radius:13px;display:grid;place-items:center;background:linear-gradient(145deg,#253b72,#16233e);border:1px solid #3a527b;color:#eaf6ff;font-weight:1000}.nav-pills{display:flex;gap:6px;padding:5px;border:1px solid #1b2940;background:#09111f;border-radius:15px}.nav-pill{width:auto;min-height:38px;margin:0;padding:7px 12px;background:transparent;border:0;box-shadow:none;color:#8291aa;font-size:12px}.nav-pill:hover{background:#111d31;box-shadow:none}.nav-pill.active{background:#182b4a;color:#dff7ff;border:1px solid #2c4b72}.hero{padding:24px;border-radius:26px;background:linear-gradient(135deg,rgba(29,52,94,.92),rgba(11,19,34,.96));border:1px solid rgba(103,154,255,.2);position:relative;overflow:hidden}.hero:after{content:"";position:absolute;width:220px;height:220px;right:-80px;top:-90px;border-radius:50%;background:rgba(54,217,232,.08);filter:blur(8px)}.eyebrow{font-size:10px;letter-spacing:2.2px;color:#7e91af;font-weight:1000}.hero h1{margin:7px 0 5px;font-size:31px;letter-spacing:-1.4px}.hero p{margin:0;color:#91a2ba;font-size:13px;line-height:1.5}.quick-grid{display:grid;grid-template-columns:1.2fr 1fr;gap:10px;margin-top:14px}.quick-action{min-height:88px;text-align:left;margin:0;padding:16px;border:1px solid #263956;background:#0b1424;border-radius:18px;box-shadow:none}.quick-action strong{display:block;font-size:15px}.quick-action small{display:block;color:#71839c;margin-top:5px;font-size:11px}.quick-action.primary{background:linear-gradient(145deg,#1c3b73,#12324b);border-color:#345f9d}.section-card{padding:20px;border-radius:23px;background:rgba(11,18,31,.92);border:1px solid #1c2b43}.section-card h2{font-size:19px;margin:0;letter-spacing:-.4px}.section-card .sub{color:#71829d;font-size:12px;margin-top:4px}.profile-hero{display:flex;align-items:center;gap:15px;padding:20px;border-radius:22px;background:linear-gradient(145deg,#111e34,#0a111e);border:1px solid #223653}.profile-avatar{width:68px;height:68px;border-radius:20px;display:grid;place-items:center;font-size:27px;font-weight:1000;background:linear-gradient(145deg,#4269b9,#203657);border:1px solid #5a7dbb}.profile-name{font-size:23px;font-weight:1000}.profile-title{font-size:12px;color:#7f92ad;margin-top:4px}.profile-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:9px;margin-top:12px}.profile-stat{padding:14px;border-radius:16px;background:#09111e;border:1px solid #1c2b43}.profile-stat b{display:block;font-size:19px;color:#dff8ff}.profile-stat span{display:block;font-size:10px;color:#70819a;margin-top:3px}.practice-head{display:flex;justify-content:space-between;align-items:flex-end;gap:10px}.practice-list{display:grid;gap:8px;margin-top:13px}.practice-set{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:13px;border-radius:16px;background:#0a1220;border:1px solid #1b2b43}.practice-set-info b{display:block;font-size:13px}.practice-set-info small{display:block;color:#71829b;margin-top:3px}.practice-select{width:auto!important;margin:0!important;min-height:20px!important}.practice-bar{height:7px;background:#101d30;border-radius:999px;overflow:hidden;margin-top:14px}.practice-bar>div{height:100%;width:0;background:linear-gradient(90deg,#5b8cff,#22d3ee);transition:width .25s}.practice-question{font-size:24px;line-height:1.38;font-weight:950;margin-top:14px}.practice-option{display:block;width:100%;text-align:left;margin-top:9px;min-height:58px;background:#0c1525;border:1px solid #263a58;border-radius:15px;padding:13px 15px}.practice-option.selected{border-color:#5b8cff;background:#13264a}.practice-option.correct{border-color:#34d399!important;background:#0d3b2e!important}.practice-option.incorrect{border-color:#fb7185!important;background:#3d1522!important}.practice-feedback{margin-top:12px;padding:12px;border-radius:14px;font-size:12px;font-weight:800}.practice-feedback.good{background:#0d3429;border:1px solid #1e8d68;color:#9cf1cf}.practice-feedback.bad{background:#391723;border:1px solid #8f2c49;color:#ffc0cc}.practice-controls{display:flex;gap:8px}.practice-controls button{flex:1}.compact-section{padding:18px}.practice-empty{padding:22px;text-align:center;color:#71829a;border:1px dashed #263650;border-radius:17px;margin-top:12px}.section-nav{display:flex;gap:8px;margin-top:4px}.section-nav button{margin:0;width:auto;min-height:42px;padding:9px 13px;font-size:12px}.you-link{background:#111d31!important;border:1px solid #263956!important}.dashboard-actions{display:flex;gap:8px;margin-top:14px}.dashboard-actions button{flex:1}.mobile-only{display:none}@media(max-width:650px){.quick-grid{grid-template-columns:1fr}.profile-grid{grid-template-columns:repeat(2,1fr)}.nav-pill{padding:7px 9px}.hero h1{font-size:27px}.practice-question{font-size:21px}}@media(max-width:430px){.topbar-brand{font-size:16px}.nav-pill{font-size:11px;padding:7px 8px}.profile-grid{grid-template-columns:1fr 1fr}.practice-controls{flex-direction:column}}

/* VNext 2 — cleaner PDF builder + premium study surfaces */
.pdf-controls{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:10px}.pdf-controls label{display:block;font-size:11px;font-weight:900;letter-spacing:.5px;color:#8193ae;margin:0 0 5px}.pdf-controls select{margin:0;min-height:48px}.quality-summary{display:flex;flex-direction:column;justify-content:center;padding:11px 13px;border:1px solid #243552;border-radius:14px;background:#08111f}.quality-summary b{font-size:12px;color:#bfefff}.quality-summary span{font-size:10px;color:#71839e;margin-top:3px}.pdf-progress-detail{font-size:10px;color:#71839e;margin-top:5px;line-height:1.35}.pdf-trust{display:flex;flex-wrap:wrap;gap:7px;margin-top:10px}.pdf-trust span{font-size:10px;color:#7890ad;padding:6px 8px;border-radius:999px;border:1px solid #1e304c;background:#08111f}.pdf-progress-wrap{animation:progressIn .2s ease}@keyframes progressIn{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:none}}@media(max-width:560px){.pdf-controls{grid-template-columns:1fr}.quality-summary{min-height:64px}}
</style></head><body><div class="container">
<div id="login" class="screen"><div class="brand">
<div class="logo">⚔️ Study<span>Battle</span></div>
<div class="tag">Login to load your saved progress 🔐</div>
</div>
<div class="card">
<div class="title">🔐 Player Login</div>
<div class="muted" style="margin-top:6px">Your XP, wins, battles and streaks are saved to your account.</div>
<input id="login_username" placeholder="Username" autocomplete="username">
<input id="login_password" type="password" placeholder="Password" autocomplete="current-password">
<button onclick="loginAccount()">🚀 Login</button>
<button class="secondary" onclick="registerAccount()">🆕 Create Account</button>
<div id="login_msg" class="small"></div>
</div></div>

<div id="dashboard" class="screen hidden">
<div class="app-shell">
  <div class="topbar">
    <div class="topbar-brand">⚔️ Study<span>Battle</span></div>
    <div class="nav-pills">
      <button class="nav-pill active" onclick="goDashboard()">Home</button>
      <button class="nav-pill" onclick="openPractice()">Practice</button>
      <button class="nav-pill" onclick="openProfile()">You</button>
    </div>
    <div id="topAvatar" class="avatar">S</div>
  </div>
  <div class="hero">
    <div class="eyebrow">YOUR STUDY HUB</div>
    <h1>Welcome back, <span id="dash_username"></span>.</h1>
    <p>Build from your notes, practice smarter, then enter the arena when you're ready.</p>
    <div class="quick-grid">
      <button class="quick-action primary" onclick="openPractice()"><strong>🎯 Practice</strong><small>Sharpen concepts from your study sets.</small></button>
      <button class="quick-action" onclick="openArena()"><strong>⚔️ Battle</strong><small>Challenge friends in a live quiz.</small></button>
    </div>
  </div>
  <div class="section-card">
    <div class="practice-head"><div><h2>Your progress</h2><div class="sub">A clean snapshot of your StudyBattle journey.</div></div><button class="nav-pill you-link" onclick="openProfile()">View profile →</button></div>
    <div class="profile-grid">
      <div class="profile-stat"><b id="dash_xp">0</b><span>XP</span></div><div class="profile-stat"><b id="dash_wins">0</b><span>WINS</span></div><div class="profile-stat"><b id="dash_battles">0</b><span>BATTLES</span></div><div class="profile-stat"><b id="dash_accuracy">0%</b><span>ACCURACY</span></div><div class="profile-stat"><b id="dash_best_streak">0</b><span>BEST STREAK</span></div><div class="profile-stat"><b id="dash_level">1</b><span>LEVEL</span></div>
    </div>
  </div>
  <div class="section-card compact-section"><div class="practice-head"><div><h2>Practice</h2><div class="sub">Choose a study set and start a focused session.</div></div><button class="nav-pill you-link" onclick="openPractice()">Open →</button></div><div id="dashboardPracticePreview" class="practice-list"><div class="practice-empty">Loading your study sets…</div></div></div>
  <div class="section-card"><div class="practice-head"><div><h2>🏆 Hall of Fame</h2><div class="sub">Top StudyBattle champions.</div></div></div><div id="hall_of_fame" class="small" style="margin-top:12px">Loading champions...</div></div>
</div></div>

<div id="profile" class="screen hidden">
<div class="app-shell">
  <div class="topbar"><button class="nav-pill" onclick="goDashboard()">← Home</button><div class="topbar-brand">You</div><div id="profileTopAvatar" class="avatar">S</div></div>
  <div class="profile-hero"><div id="profileAvatar" class="profile-avatar">S</div><div><div id="profileName" class="profile-name">Player</div><div id="profileTitle" class="profile-title">Challenger · Level 1</div></div></div>
  <div class="section-card"><h2>Stats</h2><div class="profile-grid"><div class="profile-stat"><b id="profileXp">0</b><span>XP</span></div><div class="profile-stat"><b id="profileWins">0</b><span>WINS</span></div><div class="profile-stat"><b id="profileBattles">0</b><span>BATTLES</span></div><div class="profile-stat"><b id="profileAccuracy">0%</b><span>ACCURACY</span></div><div class="profile-stat"><b id="profileBestScore">0</b><span>BEST SCORE</span></div><div class="profile-stat"><b id="profileCoins">0</b><span>COINS</span></div></div></div>
  <div class="section-card"><h2>🏅 Achievements</h2><div id="profileAchievements" class="small" style="margin-top:10px"></div></div>
  <div class="section-card"><h2>Recent battles</h2><div id="profileHistory" class="small" style="margin-top:10px"></div></div>
  <div class="dashboard-actions"><button class="secondary" onclick="openPractice()">🎯 Practice</button><button onclick="openArena()">⚔️ Battle</button></div>
  <button class="danger-btn" onclick="logout()">🚪 Logout</button>
</div></div>

<div id="practice" class="screen hidden">
<div class="app-shell">
  <div class="topbar"><button class="nav-pill" onclick="goDashboard()">← Home</button><div class="topbar-brand">🎯 Practice</div><div id="practiceTopAvatar" class="avatar">S</div></div>
  <div class="hero"><div class="eyebrow">FOCUSED STUDY</div><h1>Practice without pressure.</h1><p>Work through questions from your own uploaded study sets. No room codes, no leaderboard—just learning.</p></div>
  <div id="practiceSetup" class="section-card"><div class="practice-head"><div><h2>Choose study sets</h2><div class="sub">Select one or more sets.</div></div><select id="practiceAmount" style="width:auto;min-width:130px;margin:0"><option value="5">5 questions</option><option value="10" selected>10 questions</option><option value="15">15 questions</option><option value="20">20 questions</option><option value="30">30 questions</option></select></div><div id="practiceCatalog" class="practice-list"><div class="practice-empty">Loading study sets…</div></div><button onclick="startPractice()">Start Practice</button></div>
  <div id="practiceSession" class="section-card hidden"><div class="practice-head"><div><div class="eyebrow" id="practiceMeta">PRACTICE</div><h2 id="practiceCounter">Question 1 / 10</h2></div><strong id="practiceScore">0 correct</strong></div><div class="practice-bar"><div id="practiceBarFill"></div></div><div id="practiceQuestion" class="practice-question"></div><div id="practiceOptions"></div><div id="practiceFeedback" class="practice-feedback hidden"></div><div class="practice-controls"><button id="practiceNext" class="secondary" onclick="nextPractice()" disabled>Next question</button><button class="secondary" onclick="endPractice()">Exit</button></div></div>
  <div id="practiceDone" class="section-card hidden"><div style="font-size:44px">🎉</div><h2 id="practiceDoneTitle" style="margin-top:8px">Practice complete</h2><div id="practiceDoneText" class="sub" style="margin-top:6px"></div><div class="dashboard-actions"><button onclick="openPractice()">Practice again</button><button class="secondary" onclick="goDashboard()">Back home</button></div></div>
</div></div>

<div id="home" class="screen"><div class="brand"><div class="logo">⚔️ Study<span>Battle</span></div><div class="tag">Study. Battle. Win. 😈</div></div><div class="card"><button class="secondary" onclick="backToDashboardFromArena()" style="margin-top:0;margin-bottom:10px">← Back to Dashboard</button><div class="title">Enter the arena</div><input id="name" placeholder="Your name" autocomplete="off">
<div class="section-label">STUDY MATERIAL</div>
<div class="pdfbox">
  <div class="pdf-top"><div><div class="pdf-title">📄 Build a Study Set</div><div class="pdf-subtitle">Upload notes or a textbook PDF and turn it into playable MCQs.</div></div><div class="pdf-badge">PDF</div><div class="quality-pill">SOURCE-GROUNDED</div></div>
  <div class="pdf-grid"><input id="pdf_subject" placeholder="Subject · Physics"><input id="pdf_topic" placeholder="Study set name · Ray Optics"></div>
  <div class="pdf-controls"><div><label for="pdf_question_count">Questions to generate</label><select id="pdf_question_count"><option value="10" selected>10 MCQs</option><option value="20">20 MCQs</option><option value="30">30 MCQs</option><option value="50">50 MCQs</option><option value="75">75 MCQs</option><option value="100">100 MCQs</option><option value="150">150 MCQs</option><option value="200">200 MCQs</option></select></div><div class="quality-summary"><b>Quality mode</b><span>Source-grounded • deduplicated</span></div></div>
  <label class="file-drop" for="pdf_file"><span class="file-icon">↑</span><span><b id="pdf_file_name">Choose PDF</b><small>Text PDFs and scanned PDFs · up to 100 MB</small></span></label>
  <input id="pdf_file" type="file" accept="application/pdf,.pdf" class="visually-hidden">
  <button id="pdfUploadBtn" onclick="uploadPDF()">✨ Generate Study Set</button>
  <div id="pdf_progress_wrap" class="pdf-progress-wrap hidden">
    <div class="pdf-progress-top"><span id="pdf_stage">Preparing…</span><strong id="pdf_percent">0%</strong></div>
    <div class="pdf-progress"><div id="pdf_progress_bar"></div></div>
    <div class="pdf-progress-meta"><span id="pdf_eta">Estimating time…</span><span id="pdf_page_progress"></span></div><div id="pdf_progress_detail" class="pdf-progress-detail"></div>
  </div>
  <div id="pdf_status" class="status-line"></div><div class="pdf-trust"><span>✓ Page-aware extraction</span><span>✓ OCR fallback</span><span>✓ Duplicate filtering</span></div>
</div>
<div class="section-head"><div><div class="section-label">YOUR STUDY SETS</div><div class="small">Select one or more sets to build your battle.</div></div><button type="button" class="refresh-btn" onclick="loadCatalog()">↻ Refresh</button></div>
<div id="topic_catalog" class="topiccatalog"><div class="empty-state"><div class="empty-icon">⏳</div><span>Loading study sets…</span></div></div><div class="muted" style="margin-top:13px;font-weight:900">2. Game Mode</div><div class="modegrid"><div id="bm_classic" class="mode" onclick="setBattleMode('classic')"><span class="modeicon">⚔️</span><span class="modename">Classic</span><span class="modesub">5 questions • balanced</span></div><div id="bm_sudden_death" class="mode" onclick="setBattleMode('sudden_death')"><span class="modeicon">💀</span><span class="modename">Sudden Death</span><span class="modesub">Wrong answer = OUT</span></div><div id="bm_streak" class="mode" onclick="setBattleMode('streak')"><span class="modeicon">🔥</span><span class="modename">Streak Master</span><span class="modesub">Bigger streak bonuses</span></div><div id="bm_tournament" class="mode" onclick="setBattleMode('tournament')"><span class="modeicon">🏟️</span><span class="modename">Tournament</span><span class="modesub">3 battles • random surprises</span></div></div><div id="tournament_options" style="display:none;margin-top:10px"><div class="muted" style="font-weight:900">Tournament Battles</div><select id="session_battles"><option value="3" selected>3 Battles</option><option value="4">4 Battles</option><option value="5">5 Battles</option></select></div><div id="amount_container" style="margin-top:10px;display:block;"><div class="muted" style="font-weight:900">Number of Questions</div><select id="amount"><option value="5">5 Questions</option><option value="10" selected>10 Questions</option><option value="15">15 Questions</option><option value="20">20 Questions</option><option value="30">30 Questions</option><option value="50">50 Questions</option><option value="75">75 Questions</option><option value="100">100 Questions</option></select></div><button onclick="createRoom()">⚔️ Create Battle</button><input id="code" placeholder="Enter room code" autocomplete="off"><button class="secondary" onclick="joinRoom()">🚀 Join Battle</button></div></div>
<div id="lobby" class="screen hidden"><div class="brand"><div class="logo">⚔️ Study<span>Battle</span></div></div><div class="card"><div class="muted">ROOM CODE</div><div id="roomcode" class="roomcode"></div><div id="pack" class="muted" style="text-align:center"></div></div><div class="card"><div class="title">👥 Players</div><div id="players"></div><button id="start" onclick="startBattle()">🔥 Start Battle</button><div id="sessionInfo" class="small" style="text-align:center;margin-top:8px"></div><button id="cancel" class="danger-btn" onclick="cancelBattle()" style="margin-top:8px;">❌ Cancel Room</button></div><div class="card chatbox"><div class="title" style="font-size:18px">💬 Room Chat</div><div id="chat_lobby" class="chatmessages"><div class="chat-empty">No messages yet. Say hello! 👋</div></div><div class="chatform"><input id="chat_input_lobby" maxlength="240" placeholder="Type a message..." autocomplete="off" onkeydown="if(event.key==='Enter'){sendChat('lobby');}"><button onclick="sendChat('lobby')">SEND</button></div></div></div>
<div id="battleIntro" class="screen hidden"><div class="battle-intro-card">
<div class="intro-swords">⚔️</div>
<div class="intro-kicker">STUDYBATTLE</div>
<div id="introTopic" class="intro-topic">GET READY</div>
<div id="introMode" class="intro-mode">⚔️ CLASSIC</div>
<div id="introPlayers" class="intro-players">👥 WARRIORS</div>
<div class="intro-countdown-wrap"><div id="introCountdown" class="intro-countdown">3</div></div>
<div id="introStatus" class="intro-status">GET READY...</div>
</div></div>
<div id="battle" class="screen hidden"><div class="battlehead"><div><div id="count" style="font-weight:900"></div><div id="meta" class="muted"></div></div><div id="timer" class="timer">15</div></div><div class="card"><div class="statsgrid"><div class="statbox"><div id="st_score" class="statval">0</div><div class="statlbl">SCORE</div></div><div class="statbox"><div id="st_pos" class="statval">#-</div><div class="statlbl">POSITION</div></div><div class="statbox"><div id="st_acc" class="statval">0%</div><div class="statlbl">ACCURACY</div></div><div class="statbox"><div id="st_streak" class="statval">0</div><div class="statlbl">STREAK</div></div></div><div id="question" class="q"></div><div id="options"></div></div><div class="card"><div class="title" style="font-size:18px">🏆 LIVE RANKING</div><div id="ranking"></div></div></div>
<div id="battleResultOverlay" class="battle-result-overlay hidden" aria-live="assertive"><div id="confettiLayer"></div><div class="battle-result-card"><div class="trophy">🏆</div><div class="congrats">CONGRATULATIONS!</div><div class="winner-label">Battle Champion</div><div id="popupWinner" class="winner-name">—</div><div id="popupMessage" class="champion-line">Congratulations to the winner for winning the battle</div><button class="secondary popup-back-btn" onclick="closeWinnerPopup()">← Back</button></div></div>
<div id="sessionChampionOverlay" class="session-champion-overlay hidden" aria-live="assertive"><div class="session-champion-card"><div class="champion-flash"></div><div class="champion-shockwave"></div><div class="champion-crown">👑</div><div class="champion-kicker">🏟️ TOURNAMENT COMPLETE</div><div class="champion-heading">SESSION CHAMPION!</div><div id="sessionChampionName" class="champion-name">—</div><div id="sessionChampionScore" class="champion-sub">— Tournament XP</div><div class="meow-badge">🐱 MEOW! • CHAMPION ENERGY</div><button class="secondary" style="margin-top:24px" onclick="closeSessionChampionCelebration()">🏆 Continue to Final Results</button></div></div>
<div id="result" class="screen hidden"><div class="card"><div id="ricon" class="resulticon">🏆</div><div id="rtitle" class="resulttitle">Battle Finished</div><div id="rmsg" class="muted" style="text-align:center;margin-top:7px"></div></div>
<div class="card result-actions"><button id="nextBattleBtn" class="secondary hidden" onclick="startNextBattle()">⚔️ Start Next Battle</button><button id="leaderboardBtn" class="secondary" onclick="document.getElementById('leaderboardSection').scrollIntoView({behavior:'smooth'})" style="margin-top:12px">🏆 View Leaderboard</button></div>
<div id="sessionWinnerSection" class="card session-winner-card hidden"><div class="title">👑 Session Champion</div><div id="sessionWinnerBox" style="margin-top:8px"></div></div>
<div id="specialAwardsSection" class="card hidden"><div class="title">🎖️ Special Tournament Awards</div><div class="muted" style="font-size:13px;margin-top:4px">Based on overall performance across the entire tournament.</div><div id="battleAwards" style="margin-top:10px"></div></div>
<div id="sessionStandingsSection" class="card hidden"><div class="title">🏟️ Tournament Standings</div><div id="sessionRanking" class="podium"></div></div><div id="leaderboardSection" class="card"><div class="title" id="leaderboardTitle">🏆 Battle Leaderboard</div><div id="resultRanking" class="podium"></div></div><div id="dare" class="dare hidden"><div class="darelabel">🎰 DARE ROULETTE</div><div id="dareplayer" style="font-weight:900;margin-top:8px"></div><div id="daretext" class="daretext">Spinning dares...</div></div><button id="dashboardResultBtn" onclick="refreshDashboard()">🏠 Back to Dashboard</button></div></div>
<script>
let roomCode='',playerName='',poll=null,timerInt=null,current=-1,answered=false,packMode='mixed',battleMode='',maxTime=15,audioCtx=null,topicCatalog={};
let loggedIn=false, lastFinishedRoom=null, introTimer=null, previousRanks={}, previousStreaks={}, handledFinishKey='';

function setLoginMessage(msg){
  $('login_msg').textContent=msg||'';
}

async function loginAccount(){
  const username=$('login_username').value.trim();
  const password=$('login_password').value;
  if(!username||!password){
    setLoginMessage('Enter username and password.');
    return;
  }

  const d=await post('/api/login',{username,password});
  if(!d.success){
    setLoginMessage(d.message);
    return;
  }

  loggedIn=true;
  playerName=d.username;
  localStorage.setItem('studybattle_username',playerName);
  sessionStorage.setItem('studybattle_username',playerName);
  showDashboard(d.player);
}

async function registerAccount(){
  const username=$('login_username').value.trim();
  const password=$('login_password').value;

  if(!username||!password){
    setLoginMessage('Enter username and password first.');
    return;
  }

  const d=await post('/api/register',{username,password});
  if(!d.success){
    setLoginMessage(d.message);
    return;
  }

  loggedIn=true;
  playerName=d.username;
  localStorage.setItem('studybattle_username',playerName);
  sessionStorage.setItem('studybattle_username',playerName);
  showDashboard(d.player);
}

function avatarLetter(name){return (String(name||'S').trim()[0]||'S').toUpperCase()}
function setAvatar(name){const a=avatarLetter(name);['topAvatar','profileTopAvatar','profileAvatar','practiceTopAvatar'].forEach(id=>{const el=$(id);if(el)el.textContent=a})}
function showDashboard(p){
  $('dash_username').textContent=playerName; setAvatar(playerName);
  $('dash_xp').textContent=p.xp||0; $('dash_wins').textContent=p.wins||0; $('dash_battles').textContent=p.battles||0; $('dash_accuracy').textContent=(p.accuracy||0)+'%';
  $('dash_best_streak').textContent=p.best_streak||0; $('dash_level').textContent=p.level||1;
  const ach=p.achievements||[]; const hist=(p.history||[]).slice(-5).reverse();
  $('profileAchievements').innerHTML=ach.length?'🏅 '+ach.map(esc).join(' • '):'No badges yet — win a battle to earn one!';
  $('profileHistory').innerHTML=hist.length?hist.map(h=>`${esc(h.date||'')} • ${esc(h.topic||'Mixed')} • #${h.position} • ${h.score} XP`).join('<br>'):'No battles yet.';
  loadHallOfFame(); renderDashboardPracticePreview(); show('dashboard');
}
function goDashboard(){if(!loggedIn||!playerName)return show('login');refreshDashboard()}
function openProfile(){fetch('/api/profile?username='+encodeURIComponent(playerName),{cache:'no-store'}).then(r=>r.json()).then(d=>{if(!d.success)return;const p=d.player||{};setAvatar(playerName);$('profileName').textContent=playerName;$('profileTitle').textContent=(p.champion?'👑 Champion':'Challenger')+' · Level '+(p.level||1);$('profileXp').textContent=p.xp||0;$('profileWins').textContent=p.wins||0;$('profileBattles').textContent=p.battles||0;$('profileAccuracy').textContent=(p.accuracy||0)+'%';$('profileBestScore').textContent=p.best_score||0;$('profileCoins').textContent=p.coins||0;const ach=p.achievements||[];const hist=(p.history||[]).slice(-8).reverse();$('profileAchievements').innerHTML=ach.length?'🏅 '+ach.map(esc).join(' • '):'No badges yet — win a battle to earn one!';$('profileHistory').innerHTML=hist.length?hist.map(h=>`${esc(h.date||'')} · ${esc(h.topic||'Mixed')} · #${h.position} · ${h.score} XP`).join('<br>'):'No battles yet.';show('profile')}).catch(()=>toast('Could not load your profile.','error'))}
function openPractice(){show('practice');setAvatar(playerName);$('practiceSetup').classList.remove('hidden');$('practiceSession').classList.add('hidden');$('practiceDone').classList.add('hidden');loadPracticeCatalog()}
async function loadHallOfFame(){
  try{
    const r=await fetch('/api/dashboard',{cache:'no-store'});
    const d=await r.json();
    if(!d.success)return;
    const hiddenNames=new Set(['test','test 1','test1','jordan']);
    const top=(d.players||[]).filter(p=>!hiddenNames.has(String(p.name||'').trim().toLowerCase())).slice(0,5);
    $('hall_of_fame').innerHTML=top.length?top.map((p,i)=>`${i+1}. ${i===0?'👑':'🏆'} <strong>${esc(p.name)}</strong> — ${p.wins||0} wins • ${p.win_streak||0} streak`).join('<br>'):'No champions yet.';
  }catch(e){console.log('Hall of Fame:',e)}
}

function openArena(){
  show('home');
  $('name').value=playerName;
}

async function backToDashboardFromArena(){
  if(!loggedIn||!playerName)return show('login');
  try{
    const r=await fetch('/api/profile?username='+encodeURIComponent(playerName),{cache:'no-store'});
    const d=await r.json();
    if(d.success) return showDashboard(d.player);
  }catch(e){console.log('Dashboard:',e)}
  show('dashboard');
}

function logout(){
  loggedIn=false;
  playerName='';
  localStorage.removeItem('studybattle_username');
  sessionStorage.removeItem('studybattle_username');
  clearRoomState();
  roomCode='';
  if(poll)clearInterval(poll);
  if(timerInt)clearInterval(timerInt);
  show('login');
  $('login_password').value='';
}

async function refreshDashboard(){$('battleResultOverlay').classList.add('hidden');
  if(!loggedIn||!playerName)return;
  const r=await fetch('/api/profile?username='+encodeURIComponent(playerName),{cache:'no-store'});
  const d=await r.json();
  if(d.success)showDashboard(d.player);
}


let practiceQuestions=[],practiceIndex=0,practiceCorrect=0,practiceAnswered=false;
async function loadPracticeCatalog(){
  const el=$('practiceCatalog'); el.innerHTML='<div class="practice-empty">Loading your study sets…</div>';
  try{const r=await fetch('/api/catalog?username='+encodeURIComponent(playerName),{cache:'no-store'});const d=await r.json();if(!d.success)throw Error();let html='';Object.entries(d.catalog||{}).forEach(([subject,topics])=>{topics.forEach(t=>{html+=`<label class="practice-set"><span class="practice-set-info"><b>${esc(subject)} · ${esc(t.topic)}</b><small>${Number(t.count||0)} questions</small></span><input class="practice-select" type="checkbox" data-subject="${encodeURIComponent(subject)}" data-topic="${encodeURIComponent(t.topic)}"></label>`})});el.innerHTML=html||'<div class="practice-empty">No study sets yet. Upload a PDF from Battle → Build a Study Set.</div>'}catch(e){el.innerHTML='<div class="practice-empty">Could not load study sets. Try again.</div>'}}
function practiceSelections(){return [...document.querySelectorAll('#practiceCatalog .practice-select:checked')].map(x=>({subject:decodeURIComponent(x.dataset.subject),topic:decodeURIComponent(x.dataset.topic)}))}
async function startPractice(){const selections=practiceSelections();if(!selections.length)return toast('Select at least one study set.','error');const amount=Number($('practiceAmount').value||10);try{const d=await post('/api/practice_questions',{username:playerName,selections,amount});if(!d.success)return toast(d.message||'Could not start practice.','error');practiceQuestions=d.questions||[];practiceIndex=0;practiceCorrect=0;practiceAnswered=false;$('practiceSetup').classList.add('hidden');$('practiceDone').classList.add('hidden');$('practiceSession').classList.remove('hidden');renderPracticeQuestion()}catch(e){toast('Could not start practice.','error')}}
function renderPracticeQuestion(){const q=practiceQuestions[practiceIndex];if(!q)return finishPractice();practiceAnswered=false;$('practiceCounter').textContent=`Question ${practiceIndex+1} / ${practiceQuestions.length}`;$('practiceScore').textContent=`${practiceCorrect} correct`;$('practiceBarFill').style.width=(practiceIndex/practiceQuestions.length*100)+'%';$('practiceMeta').textContent=`${q.subject} · ${q.topic}`;$('practiceQuestion').textContent=q.q;$('practiceOptions').innerHTML='';$('practiceFeedback').className='practice-feedback hidden';$('practiceFeedback').textContent='';$('practiceNext').disabled=true;q.options.forEach((o,i)=>{const b=document.createElement('button');b.className='practice-option';b.textContent=o;b.onclick=()=>answerPractice(i,b);$('practiceOptions').appendChild(b)})}
function answerPractice(i,btn){if(practiceAnswered)return;practiceAnswered=true;const q=practiceQuestions[practiceIndex];const opts=[...document.querySelectorAll('.practice-option')];opts.forEach(x=>x.disabled=true);if(i===q.answer){practiceCorrect++;btn.classList.add('correct');$('practiceFeedback').className='practice-feedback good';$('practiceFeedback').textContent='✓ Correct — nice work.'}else{btn.classList.add('incorrect');if(opts[q.answer])opts[q.answer].classList.add('correct');$('practiceFeedback').className='practice-feedback bad';$('practiceFeedback').textContent='Not quite. The highlighted answer is correct.'}$('practiceScore').textContent=`${practiceCorrect} correct`;$('practiceNext').disabled=false}
function nextPractice(){if(!practiceAnswered)return;if(practiceIndex<practiceQuestions.length-1){practiceIndex++;renderPracticeQuestion()}else finishPractice()}
function finishPractice(){const total=practiceQuestions.length||1;const pct=Math.round(practiceCorrect/total*100);$('practiceSession').classList.add('hidden');$('practiceDone').classList.remove('hidden');$('practiceDoneTitle').textContent=pct>=80?'Excellent session!':pct>=60?'Good practice session!':'Keep practicing!';$('practiceDoneText').textContent=`You scored ${practiceCorrect}/${total} (${pct}%). Review the weaker topics and try again.`}
function endPractice(){practiceQuestions=[];$('practiceSession').classList.add('hidden');$('practiceDone').classList.add('hidden');$('practiceSetup').classList.remove('hidden');loadPracticeCatalog()}
async function renderDashboardPracticePreview(){const el=$('dashboardPracticePreview');if(!el)return;try{const r=await fetch('/api/catalog?username='+encodeURIComponent(playerName),{cache:'no-store'});const d=await r.json();let items=[];Object.entries(d.catalog||{}).forEach(([subject,topics])=>topics.forEach(t=>items.push({subject,topic:t.topic,count:t.count||0})));items=items.slice(0,3);el.innerHTML=items.length?items.map(x=>`<div class="practice-set"><span class="practice-set-info"><b>${esc(x.subject)} · ${esc(x.topic)}</b><small>${x.count} questions ready</small></span><span>›</span></div>`).join(''):'<div class="practice-empty">No study sets yet. Upload your first PDF to begin.</div>'}catch(e){el.innerHTML='<div class="practice-empty">Your study sets will appear here.</div>'}}

window.addEventListener('load',async()=>{
  loadCatalog();
  const saved=sessionStorage.getItem('studybattle_username') || localStorage.getItem('studybattle_username');

  if(saved){
    try{
      const r=await fetch('/api/profile?username='+encodeURIComponent(saved),{cache:'no-store'});
      const d=await r.json();
      if(d.success){
        loggedIn=true;
        playerName=saved;
        sessionStorage.setItem('studybattle_username',playerName);
        const savedRoom=restoreRoomState();
        if(savedRoom && savedRoom.code && savedRoom.name && savedRoom.name.toLowerCase()===saved.toLowerCase()){
          roomCode=savedRoom.code.toUpperCase();
          $('name').value=playerName;
          startPolling();
          return;
        }
        showDashboard(d.player);
        return;
      }
    }catch(e){}
  }
  clearRoomState();
  sessionStorage.removeItem('studybattle_username');
  show('login');
});


document.addEventListener('change',e=>{if(e.target&&e.target.id==='pdf_file'){const f=e.target.files[0];$('pdf_file_name').textContent=f?f.name:'Choose PDF';}});
const $=id=>document.getElementById(id);let currentScreen='';function show(id){if(currentScreen===id)return;document.querySelectorAll('.screen').forEach(x=>x.classList.add('hidden'));$(id).classList.remove('hidden');currentScreen=id}
function esc(t){let d=document.createElement('div');d.textContent=t;return d.innerHTML}
function toast(message,type='info'){let host=$('toastHost');if(!host){host=document.createElement('div');host.id='toastHost';document.body.appendChild(host)}let el=document.createElement('div');el.className='toast '+type;el.textContent=message;host.appendChild(el);setTimeout(()=>{el.classList.add('out');setTimeout(()=>el.remove(),220)},2600)}
function setPack(m){packMode=m;document.querySelectorAll('#home .modegrid:nth-of-type(1) .mode').forEach(x=>x.classList.remove('active'));$('pack_'+m).classList.add('active')}
let pdfPollTimer=null;
let pdfStartedAt=0;

function formatEta(sec){
  sec=Math.max(0,Math.round(Number(sec)||0));
  if(sec<=0)return 'Almost done';
  if(sec<60)return `About ${sec} sec left`;
  const m=Math.floor(sec/60),s=sec%60;
  return s?`About ${m} min ${s} sec left`:`About ${m} min left`;
}
function setPdfProgress(percent,stage,message,meta={}){
  const wrap=$('pdf_progress_wrap'); if(wrap)wrap.classList.remove('hidden');
  const pct=Math.max(0,Math.min(100,Number(percent)||0));
  $('pdf_progress_bar').style.width=pct+'%'; $('pdf_percent').textContent=Math.round(pct)+'%';
  $('pdf_stage').textContent=stage||'Processing…'; $('pdf_status').textContent=message||'';
  $('pdf_page_progress').textContent=meta.current_page&&meta.total_pages?`Page ${meta.current_page}/${meta.total_pages}`:'';
  $('pdf_eta').textContent=meta.eta_seconds!=null?formatEta(meta.eta_seconds):'Estimating time…';
  const detail=[];
  if(meta.target_questions)detail.push(`Target: ${meta.target_questions} MCQs`);
  if(meta.extracted_words)detail.push(`${Number(meta.extracted_words).toLocaleString()} words indexed`);
  if(meta.ocr_pages)detail.push(`OCR: ${meta.ocr_pages} page${meta.ocr_pages==1?'':'s'}`);
  if(meta.questions_added!=null)detail.push(`Created: ${meta.questions_added}`);
  $('pdf_progress_detail').textContent=detail.join(' • ');
}
async function pollPDFJob(jobId,fileName){
  try{
    const r=await fetch('/api/pdf_job/'+encodeURIComponent(jobId),{cache:'no-store'}); const d=await r.json();
    if(!d.success)throw new Error(d.message||'Job expired');
    const j=d.job||{};
    const labels={extracting:'Extracting text…',cleaning:'Cleaning & organizing…',indexing:'Indexing study material…',generating:'Generating quality MCQs…',quality_check:'Checking duplicates & quality…',complete:'Complete',starting:'Preparing…',queued:'Queued…'};
    setPdfProgress(j.progress||0,labels[j.stage]||'Processing…',j.message||'',j);
    if(j.status==='complete'){
      clearInterval(pdfPollTimer);pdfPollTimer=null;
      $('pdf_status').textContent=`✅ ${j.message} ${j.ocr_pages?`OCR used on ${j.ocr_pages} scanned page(s).`:''}`;
      $('pdf_file').value='';$('pdf_topic').value=''; await loadCatalog();
      toast(`${j.questions_added||0} questions added to ${j.subject} → ${j.topic}.`,'success');
      $('pdfUploadBtn').disabled=false;$('pdfUploadBtn').textContent='✨ Generate Study Set';
    }else if(j.status==='error'){
      clearInterval(pdfPollTimer);pdfPollTimer=null;
      $('pdf_status').textContent='❌ '+(j.message||'PDF processing failed.');
      $('pdfUploadBtn').disabled=false;$('pdfUploadBtn').textContent='✨ Generate Study Set';
    }
  }catch(e){
    clearInterval(pdfPollTimer);pdfPollTimer=null;
    $('pdf_status').textContent='❌ Could not read processing status. Please refresh and try again.';
    $('pdfUploadBtn').disabled=false;$('pdfUploadBtn').textContent='✨ Generate Study Set';
  }
}
async function uploadPDF(){
  const file=$('pdf_file').files[0]; if(!file)return toast('Choose a PDF first.','error');
  if(file.size>100*1024*1024)return toast('PDF must be 100 MB or smaller.','error');
  const count=Math.max(5,Math.min(200,Number($('pdf_question_count').value)||10));
  const btn=$('pdfUploadBtn'); btn.disabled=true; btn.textContent='⏳ Uploading PDF…';
  pdfStartedAt=Date.now(); setPdfProgress(1,'Uploading…','Sending the PDF to StudyBattle…',{target_questions:count});
  try{
    const fd=new FormData(); fd.append('pdf',file); fd.append('subject',$('pdf_subject').value.trim()||'General'); fd.append('topic',$('pdf_topic').value.trim()||file.name.replace(/\.pdf$/i,'')); fd.append('username',playerName); fd.append('question_count',count);
    const r=await fetch('/api/upload_pdf',{method:'POST',body:fd}); const d=await r.json();
    if(!d.success){$('pdf_status').textContent='❌ '+(d.message||'PDF upload failed.');btn.disabled=false;btn.textContent='✨ Generate Study Set';return;}
    btn.textContent='⏳ Processing…'; clearInterval(pdfPollTimer); pdfPollTimer=setInterval(()=>pollPDFJob(d.job_id,file.name),900); await pollPDFJob(d.job_id,file.name);
  }catch(e){$('pdf_status').textContent='❌ Upload failed. Please try again.';btn.disabled=false;btn.textContent='✨ Generate Study Set';}
}

async function loadCatalog(){
  try{
    const user=encodeURIComponent(playerName||'');
    const r=await fetch('/api/catalog?username='+user,{cache:'no-store'});
    const d=await r.json();
    if(!d.success)throw new Error(d.message||'Could not load study sets');
    topicCatalog=d.catalog||{};
    const el=$('topic_catalog');
    el.innerHTML='';
    let total=0;
    Object.entries(topicCatalog).forEach(([subject,topics])=>{
      const box=document.createElement('div');
      box.className='subjectbox';
      box.innerHTML='<div class="subjecttitle"><span>📚 '+esc(subject)+'</span><span class="set-count">'+topics.reduce((n,t)=>n+(t.count||0),0)+' questions</span></div>';
      topics.forEach(item=>{
        total++;
        const row=document.createElement('div');
        row.className='studyset-row';
        const label=document.createElement('label');
        label.className='topiccheck';
        label.innerHTML='<input type="checkbox" class="topic-choice" data-subject="'+encodeURIComponent(subject)+'" data-topic="'+encodeURIComponent(item.topic)+'"> <span><b>'+esc(item.topic)+'</b><small>'+Number(item.count||0)+' questions</small></span>';
        row.appendChild(label);
        if(item.deletable){
          const del=document.createElement('button');
          del.type='button'; del.className='icon-delete'; del.title='Delete study set'; del.setAttribute('aria-label','Delete '+item.topic); del.textContent='🗑️';
          del.addEventListener('click',()=>deleteStudySet(subject,item.topic));
          row.appendChild(del);
        }
        box.appendChild(row);
      });
      el.appendChild(box);
    });
    if(!total)el.innerHTML='<div class="empty-state"><div class="empty-icon">📚</div><b>No study sets yet</b><span>Upload a PDF above to create your first playable set.</span></div>';
  }catch(e){
    $('topic_catalog').innerHTML='<div class="empty-state"><b>Could not load study sets</b><span>Tap Refresh to try again.</span></div>';
  }
}

async function deleteStudySet(subject,topic){
  if(!loggedIn||!playerName)return toast('Please log in first.','error');
  if(!confirm('Delete the study set “'+topic+'” and all of its questions? This cannot be undone.'))return;
  try{
    const d=await post('/api/delete_study_set',{username:playerName,subject,topic});
    if(!d.success)return toast(d.message||'Could not delete study set.','error');
    document.querySelectorAll('.topic-choice:checked').forEach(x=>{
      if(decodeURIComponent(x.dataset.subject||'')===subject&&decodeURIComponent(x.dataset.topic||'')===topic)x.checked=false;
    });
    await loadCatalog();
    toast('Study set deleted.','success');
  }catch(e){toast('Delete failed. Please try again.','error')}
}

function selectedTopics(){
  return [...document.querySelectorAll('.topic-choice:checked')].map(x=>({
    subject:decodeURIComponent(x.getAttribute('data-subject')||''),
    topic:decodeURIComponent(x.getAttribute('data-topic')||'')
  }));
}

function saveRoomState(){
  if(roomCode && playerName){
    sessionStorage.setItem('studybattle_room',JSON.stringify({code:roomCode,name:playerName}));
  }
}
function clearRoomState(){sessionStorage.removeItem('studybattle_room');}
function restoreRoomState(){
  try{return JSON.parse(sessionStorage.getItem('studybattle_room')||'null')}catch(e){return null}
}

function setBattleMode(m){const el=$('bm_'+m);if(!el)return;const wasSelected=el.classList.contains('active');document.querySelectorAll('#home .modegrid .mode').forEach(x=>x.classList.remove('active'));if(wasSelected){battleMode='';}else{battleMode=m;el.classList.add('active');}const isTournament=battleMode==='tournament';$('tournament_options').style.display=isTournament?'block':'none';$('amount_container').style.display='block';}
function initAudio(){if(!audioCtx)audioCtx=new(window.AudioContext||window.webkitAudioContext)()}
function playSound(type){try{initAudio();if(!audioCtx)return;let osc=audioCtx.createOscillator(),gain=audioCtx.createGain();osc.connect(gain);gain.connect(audioCtx.destination);let now=audioCtx.currentTime;if(type==='correct'){osc.frequency.setValueAtTime(523.25,now);osc.frequency.setValueAtTime(659.25,now+0.1);gain.gain.setValueAtTime(0.2,now);gain.gain.exponentialRampToValueAtTime(0.01,now+0.3);osc.start(now);osc.stop(now+0.3)}else if(type==='wrong'){osc.type='sawtooth';osc.frequency.setValueAtTime(200,now);osc.frequency.setValueAtTime(120,now+0.1);gain.gain.setValueAtTime(0.2,now);gain.gain.exponentialRampToValueAtTime(0.01,now+0.3);osc.start(now);osc.stop(now+0.3)}else if(type==='tick'){osc.frequency.setValueAtTime(800,now);gain.gain.setValueAtTime(0.05,now);gain.gain.exponentialRampToValueAtTime(0.001,now+0.05);osc.start(now);osc.stop(now+0.05)}else if(type==='finish'){osc.frequency.setValueAtTime(440,now);osc.frequency.setValueAtTime(880,now+0.2);gain.gain.setValueAtTime(0.2,now);gain.gain.exponentialRampToValueAtTime(0.01,now+0.5);osc.start(now);osc.stop(now+0.5)}else if(type==='victory'){osc.type='triangle';[523.25,659.25,783.99,1046.5].forEach((f,i)=>{osc.frequency.setValueAtTime(f,now+i*0.12)});gain.gain.setValueAtTime(0.22,now);gain.gain.exponentialRampToValueAtTime(0.01,now+0.75);osc.start(now);osc.stop(now+0.75)}else if(type==='countdown'){osc.type='sine';osc.frequency.setValueAtTime(587.33,now);gain.gain.setValueAtTime(0.075,now);gain.gain.exponentialRampToValueAtTime(0.008,now+0.12);osc.start(now);osc.stop(now+0.12)}else if(type==='go'){osc.type='triangle';[523.25,783.99,1046.5].forEach((f,i)=>osc.frequency.setValueAtTime(f,now+i*0.09));gain.gain.setValueAtTime(0.18,now);gain.gain.exponentialRampToValueAtTime(0.01,now+0.4);osc.start(now);osc.stop(now+0.4)}else if(type==='meow'){osc.type='sine';osc.frequency.setValueAtTime(980,now);osc.frequency.exponentialRampToValueAtTime(620,now+0.18);osc.frequency.exponentialRampToValueAtTime(900,now+0.34);osc.frequency.exponentialRampToValueAtTime(430,now+0.58);gain.gain.setValueAtTime(0.46,now);gain.gain.exponentialRampToValueAtTime(0.22,now+0.18);gain.gain.exponentialRampToValueAtTime(0.01,now+0.7);osc.start(now);osc.stop(now+0.7);const sub=audioCtx.createOscillator(),sg=audioCtx.createGain();sub.type='triangle';sub.frequency.setValueAtTime(490,now);sub.frequency.exponentialRampToValueAtTime(260,now+0.62);sg.gain.setValueAtTime(0.16,now);sg.gain.exponentialRampToValueAtTime(0.005,now+0.7);sub.connect(sg);sg.connect(audioCtx.destination);sub.start(now);sub.stop(now+0.7)}}catch(e){}}
async function post(url,body){let r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});return r.json()}
async function createRoom(){
  playerName=$('name').value.trim();
  if(!playerName)return toast('Enter your name.','error');
  let selections=selectedTopics();
  if(!selections.length)return toast('Select at least one study set.','error');
  if(!battleMode)return toast('Select a game mode.','error');
  const questionAmount=Math.max(5,Math.min(30,parseInt($('amount').value,10)||5));
  const sessionBattles=battleMode==='tournament'?Math.max(3,Math.min(5,parseInt($('session_battles').value,10)||3)):1;
  const createBtn=document.querySelector('button[onclick="createRoom()"]');if(createBtn?.disabled)return; if(createBtn){createBtn.disabled=true;createBtn.textContent='⏳ Creating Battle…'} let d; try{d=await post('/api/create_room',{name:playerName,selections:selections,mode:packMode,battle_mode:battleMode,amount:questionAmount,session_battles:sessionBattles});}catch(e){if(createBtn){createBtn.disabled=false;createBtn.textContent='⚔️ Create Battle'}return toast('Network error. Please try again.','error')} if(createBtn){createBtn.disabled=false;createBtn.textContent='⚔️ Create Battle'}
  if(!d.success)return toast(d.message,'error');
  roomCode=d.code;
  saveRoomState();
  enterLobby();
}
async function joinRoom(){
  playerName=$('name').value.trim();
  roomCode=$('code').value.trim().toUpperCase();
  if(!playerName||!roomCode)return toast('Enter your name and room code.','error');
  const joinBtn=document.querySelector('button[onclick="joinRoom()"]');
  if(joinBtn?.disabled)return;
  if(joinBtn){joinBtn.disabled=true;joinBtn.textContent='⏳ Joining…'}
  let d;
  try{d=await post('/api/join_room',{name:playerName,code:roomCode});}catch(e){if(joinBtn){joinBtn.disabled=false;joinBtn.textContent='🚀 Join Battle'}return toast('Network error. Please try again.','error')}
  if(joinBtn){joinBtn.disabled=false;joinBtn.textContent='🚀 Join Battle'}
  if(!d.success)return toast(d.message,'error');
  saveRoomState();
  enterLobby();
}
function enterLobby(){show('lobby');$('roomcode').textContent=roomCode;saveRoomState();startPolling()}
async function startBattle(){let b=$('start');if(b.disabled)return;b.disabled=true;b.dataset.busy='1';b.textContent='⏳ Starting…';try{let d=await post('/api/start_room',{code:roomCode,name:playerName});if(!d.success)toast(d.message,'error')}finally{b.disabled=false;b.dataset.busy='';b.textContent='🔥 Start Battle'}}
async function startNextBattle(){previousRanks={};previousStreaks={};handledFinishKey='';show('lobby');startPolling();await startBattle()}
async function cancelBattle(){if(!confirm("Are you sure you want to cancel this room?"))return;let d=await post('/api/cancel_room',{code:roomCode,name:playerName});if(d.success){clearRoomState();roomCode='';show('home')}else toast(d.message,'error')}
function startPolling(){if(poll)clearInterval(poll);checkRoom();poll=setInterval(checkRoom,350)}
async function checkRoom(){
  if(!roomCode||!playerName)return;
  try{
    let r=await fetch('/api/room?code='+encodeURIComponent(roomCode),{cache:'no-store'});
    let d=await r.json();
    if(!d.success){
      clearRoomState();
      if(poll)clearInterval(poll);
      if(timerInt)clearInterval(timerInt);
      show('home');
      $('name').value=playerName;
      return;
    }
    saveRoomState();
    let room=d.room;
    updatePlayers(room);
    if(room.status==='waiting') renderChat(room);
    if(room.status==='waiting'){
      show('lobby');
      $('pack').textContent='📚 '+room.subject+' • '+room.topic+' • '+(room.selections&&room.selections.length?room.selections.map(x=>x.subject+' / '+x.topic).join(' | '):'')+' • '+formatMode(room.battle_mode)+' • '+room.total_questions+' questions';
    }
    if(room.status==='intro'){
      handledFinishKey='';
      showBattleIntro(room);
    }
    if(room.status==='playing'){
      window._introStartedMs=null;
      if(introTimer){clearInterval(introTimer);introTimer=null;}
      show('battle');
      maxTime=room.question_time||15;
      if(room.question_index!==current){current=room.question_index;answered=false;showQuestion(room)}
      updateRanking(room);
    }
    if(room.status==='finished'){
      if(timerInt)clearInterval(timerInt);
      const finishKey=room.code+':'+(room.session_battle||1);
      if(handledFinishKey!==finishKey){
        handledFinishKey=finishKey;
        lastFinishedRoom=room;
        showWinnerPopup(room);
      }
      // Keep polling so non-host players automatically enter the next tournament battle.
    }
  }catch(e){
    // Temporary network errors should NOT kick the player out. Keep polling.
    console.log('Room sync:',e);
  }
}
function renderChat(room){
  const chats=room.chat||[];
  ['lobby'].forEach(where=>{
    const el=$('chat_'+where);
    if(!el)return;
    if(!chats.length){el.innerHTML='<div class="chat-empty">No messages yet. Say hello! 👋</div>';return;}
    el.innerHTML=chats.map(m=>{
      const time=new Date((m.time||Date.now()/1000)*1000).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'});
      return '<div class="chatmsg"><div class="chatname">'+esc(m.name)+(m.system?' · SYSTEM':'')+'<span class="chattime">'+esc(time)+'</span></div><div class="chattext">'+esc(m.text)+'</div></div>';
    }).join('');
    el.scrollTop=el.scrollHeight;
  });
}
async function sendChat(where){
  if(where!=='lobby')return;
  const input=$('chat_input_'+where);
  if(!input||!roomCode||!playerName)return;
  const text=input.value.trim();
  if(!text)return;
  input.disabled=true;
  try{
    const d=await post('/api/chat',{code:roomCode,name:playerName,text});
    if(!d.success)toast(d.message,'error');
    else input.value='';
  }catch(e){console.log('Chat send:',e)}
  input.disabled=false;
  input.focus();
}

function formatMode(m){return ({classic:'⚔️ CLASSIC',sudden_death:'💀 SUDDEN DEATH',streak:'🔥 STREAK MASTER',tournament:'🏟️ TOURNAMENT'})[m]||String(m||'CLASSIC').toUpperCase()}
function updatePlayers(room){$('sessionInfo').textContent=room.session_battles>1?`🏟️ Tournament: Battle ${room.session_battle} / ${room.session_battles}`:'⚔️ Single Battle';$('players').innerHTML=room.players.map(p=>`<div class="row"><span>${esc(p.name)}${p.name.toLowerCase()===room.host.toLowerCase()?'<span class="badge">HOST</span>':''}</span><span class="score">${p.score} XP</span></div>`).join('');let isHost=playerName.toLowerCase()===room.host.toLowerCase();$('start').style.display=isHost?'block':'none';$('cancel').style.display=isHost?'block':'none'}
function getStreakFire(s){if(s>=5)return '🔥🔥🔥';if(s>=3)return '🔥🔥';if(s>=2)return '🔥';return ''}
function showBattleIntro(room){
  const duration=(room.intro_duration||10)*1000;
  const startedMs=(room.intro_started||Date.now()/1000)*1000;

  // The intro is keyed to the server timestamp. Polling must never rebuild the animation.
  if(window._introStartedMs===startedMs){
    if(currentScreen!=='battleIntro')show('battleIntro');
    return;
  }
  if(introTimer)clearInterval(introTimer);
  window._introStartedMs=startedMs;
  show('battleIntro');

  $('introTopic').textContent=(room.selections&&room.selections.length)
    ? room.selections.map(x=>x.topic).join(' • ')
    : (room.topic||'BATTLE');
  $('introMode').textContent=formatMode(room.battle_mode);
  $('introPlayers').textContent='👥 '+room.players.length+' WARRIORS';
  if(room.surprise && room.battle_mode==='tournament'){
    $('introMode').textContent='🏟️ '+room.surprise.name;
    $('introStatus').textContent=room.surprise.description||'SPECIAL ROUND';
  }

  const countdown=$('introCountdown');
  countdown.dataset.last='';
  function renderAndSound(){
    const elapsed=Math.max(0,Date.now()-startedMs);
    const left=Math.max(0,duration-elapsed);
    const sec=Math.ceil(left/1000);
    countdown.textContent=sec>0?sec:'⚔️';
    if(sec>0){
      $('introStatus').textContent=(room.surprise&&room.battle_mode==='tournament')
        ? room.surprise.description
        : (sec<=3?'GET READY...':'THE BATTLE IS ABOUT TO BEGIN');
    }else{
      $('introStatus').textContent='BATTLE!';
    }
    const previous=countdown.dataset.last;
    if(String(sec)!==previous){
      countdown.dataset.last=String(sec);
      if(sec>0)playSound('countdown'); else playSound('go');
    }
    if(elapsed>=duration){clearInterval(introTimer);introTimer=null;}
  }
  renderAndSound();
  introTimer=setInterval(renderAndSound,50);
}
function showQuestion(room){let q=room.question;if(!q)return;let finalTag=room.is_final_question?' (🔥 TRIPLE POINTS!)':'';$('count').textContent='QUESTION '+(room.question_index+1)+' / '+room.total_questions+finalTag;$('meta').textContent=q.subject+' • '+q.topic+(room.surprise?' • '+room.surprise.name:'');$('question').textContent=q.q;$('options').innerHTML='';q.options.forEach((o,i)=>{let b=document.createElement('button');b.className='opt';b.textContent=o;b.onclick=()=>answerQuestion(i,room.question_index);$('options').appendChild(b)});startTimer(room.question_started)}
function startTimer(start){if(timerInt)clearInterval(timerInt);function tick(){let left=Math.max(0,Math.ceil(maxTime-((Date.now()/1000)-start)));$('timer').textContent=left;if(left<=3)playSound('tick');if(left<=5)$('timer').classList.add('danger');else $('timer').classList.remove('danger');if(left<=0)clearInterval(timerInt)}tick();timerInt=setInterval(tick,250)}
async function answerQuestion(a,qi){if(answered)return;answered=true;let bs=document.querySelectorAll('.opt');bs.forEach(b=>b.disabled=true);try{let d=await post('/api/answer_room',{code:roomCode,name:playerName,answer:a,question_index:qi});if(!d.success){answered=false;bs.forEach(b=>b.disabled=false);return toast(d.message,'error')}if(d.correct){playSound('correct');if(bs[a])bs[a].classList.add('correct');let spTxt=d.speed_bonus?` ⚡+${d.speed_bonus} Speed`:'';feedback('✓ CORRECT!',`+${d.points} XP${spTxt}`,true)}else{playSound('wrong');if(bs[a])bs[a].classList.add('wrong-choice');if(bs[d.correct_answer_index])bs[d.correct_answer_index].classList.add('right-choice');feedback('✕ WRONG!',`Correct answer: ${d.correct_answer}`,false)}}catch(e){answered=false;bs.forEach(b=>b.disabled=false)}}
function feedback(title,sub,good){let x=document.createElement('div');x.className='feedback '+(good?'good':'bad');x.innerHTML='<b>'+esc(title)+'</b><div class="muted" style="margin-top:6px">'+esc(sub)+'</div>';document.body.appendChild(x);setTimeout(()=>x.remove(),1050)}
function showBattleMoment(text, sound='finish'){
  const old=document.querySelector('.battle-moment');
  if(old)old.remove();
  const x=document.createElement('div');x.className='battle-moment';x.textContent=text;
  document.body.appendChild(x);
  playSound(sound);
  setTimeout(()=>x.remove(),1400);
}
function updateRanking(room){let s=[...room.players].sort((a,b)=>b.score-a.score||b.correct-a.correct);$('ranking').innerHTML=s.map((p,i)=>`<div class="rank"><div class="rankleft"><div class="ranknum">${i===0?'🥇':i===1?'🥈':i===2?'🥉':i+1}</div><strong>${esc(p.name)}</strong>${p.streak>=2?`<span style="margin-left:5px">${getStreakFire(p.streak)} ${p.streak}</span>`:''}${p.elimination_warning?'<span class="warning-badge">⚠️ DANGER</span>':''}${p.eliminated?'<span class="warning-badge">💀 OUT</span>':''}</div><strong class="score">${p.score} XP</strong></div>`).join('');let me=s.find(p=>p.name.toLowerCase()===playerName.toLowerCase());if(me){const myPos=s.indexOf(me)+1;const oldPos=previousRanks[playerName]||myPos;const oldStreak=previousStreaks[playerName]||0;$('st_score').textContent=me.score;$('st_pos').textContent='#'+myPos;$('st_acc').textContent=me.answered?Math.round((me.correct/me.answered)*100)+'%':'0%';$('st_streak').textContent=me.streak+(me.streak>=2?' 🔥':'');if(me.streak>=3&&me.streak>oldStreak)showBattleMoment(`${getStreakFire(me.streak)} ${me.streak} STREAK!`,'correct');if(myPos<oldPos)showBattleMoment(`🚀 You moved to #${myPos}!`,'finish');if(myPos===1&&oldPos>1)showBattleMoment('👑 YOU TOOK 1ST PLACE!','victory');previousRanks[playerName]=myPos;previousStreaks[playerName]=me.streak}}
function showWinnerPopup(room){
  const overlay=$('battleResultOverlay');
  if(!overlay)return;
  lastFinishedRoom=room;
  const winner=room.winner||[...room.players].sort((a,b)=>b.score-a.score||b.correct-a.correct)[0]?.name||'Unknown';
  $('popupWinner').textContent=winner;
  const isWinner=winner.toLowerCase()===playerName.toLowerCase();
  $('popupMessage').textContent=isWinner
    ? 'Congratulations, you won the battle'
    : `Congratulations to ${winner} for winning the battle`;

  const layer=$('confettiLayer');
  layer.innerHTML='';
  for(let i=0;i<90;i++){
    const c=document.createElement('span');
    c.className='confetti-piece';
    c.style.left=(Math.random()*100)+'%';
    c.style.animationDelay=(Math.random()*0.9)+'s';
    c.style.animationDuration=(2.1+Math.random()*1.5)+'s';
    c.style.transform='rotate('+Math.random()*360+'deg)';
    c.style.background=['#facc15','#38bdf8','#22c55e','#fb7185','#a78bfa'][Math.floor(Math.random()*5)];
    layer.appendChild(c);
  }
  for(let i=0;i<12;i++){
    const sp=document.createElement('span');
    sp.className='sparkle';
    sp.textContent='✨';
    sp.style.left=(5+Math.random()*90)+'%';
    sp.style.top=(10+Math.random()*75)+'%';
    sp.style.animationDelay=(Math.random()*0.8)+'s';
    layer.appendChild(sp);
  }
  overlay.classList.remove('hidden');
  playSound('victory');
}

function closeWinnerPopup(){
  $('battleResultOverlay').classList.add('hidden');
  if(lastFinishedRoom){
    const finished=lastFinishedRoom;
    lastFinishedRoom=null;
    showResult(finished);
  }
}

function showSessionChampionCelebration(room){
  if(!room || room.battle_mode!=='tournament' || !room.session_finished || !room.session_champion)return;
  const overlay=$('sessionChampionOverlay');
  if(!overlay)return;
  $('sessionChampionName').textContent=room.session_champion;
  $('sessionChampionScore').textContent=`${(room.session_scores||{})[room.session_champion]||0} Tournament XP`;
  overlay.classList.remove('hidden');
  const layer=document.createElement('div');layer.dataset.championConfetti='1';layer.style.cssText='position:absolute;inset:0;pointer-events:none;overflow:hidden';
  for(let i=0;i<150;i++){const c=document.createElement('span');c.className='confetti-piece';c.style.left=(Math.random()*100)+'%';c.style.animationDelay=(Math.random()*1.2)+'s';c.style.animationDuration=(2.2+Math.random()*1.8)+'s';c.style.background=['#facc15','#fde68a','#38bdf8','#22c55e','#fb7185','#a78bfa'][Math.floor(Math.random()*6)];layer.appendChild(c)}
  overlay.appendChild(layer);
  playSound('meow');
  setTimeout(()=>playSound('victory'),260);
}
function closeSessionChampionCelebration(){
  $('sessionChampionOverlay').classList.add('hidden');
  const layer=$('sessionChampionOverlay').querySelector('[data-champion-confetti]');
  if(layer)layer.remove();
}

async function showResult(room){
  const sessionDone=!!room.session_finished;
  const isTournament=room.battle_mode==='tournament';
  const hiddenNames=new Set(['test','test1','test 1','jordan']);
  let s=[...room.players].sort((a,b)=>b.score-a.score||b.correct-a.correct);
  const visiblePlayers=isTournament?s:s.filter(p=>!hiddenNames.has(p.name.trim().toLowerCase()));
  let me=visiblePlayers.find(p=>p.name.toLowerCase()===playerName.toLowerCase()),pos=me?visiblePlayers.indexOf(me)+1:0;

  if(pos===1){
    $('ricon').textContent='👑';$('rtitle').textContent='YOU WON THIS BATTLE!';
    let rw=(room.rewards||{})[playerName]||{};
    $('rmsg').textContent=isTournament
      ? `Battle ${room.session_battle||1} complete • Tournament points carried forward`
      : `Battle complete • +${rw.coins||100} 💎 coins`;
  }else{
    $('ricon').textContent='⚔️';$('rtitle').textContent=isTournament?`BATTLE ${room.session_battle||1} COMPLETE`:'BATTLE COMPLETE';
    $('rmsg').textContent=pos?`You finished #${pos} in this battle.`:'Battle complete.';
  }

  // Tournament: never show a battle leaderboard or per-battle special awards.
  if(isTournament){
    $('leaderboardSection').classList.add('hidden');
    $('specialAwardsSection').classList.toggle('hidden', !sessionDone);
    $('sessionWinnerSection').classList.toggle('hidden', !sessionDone || !room.session_champion);

    const totals=Object.entries(room.session_scores||{}).sort((a,b)=>b[1]-a[1]);
    $('sessionStandingsSection').classList.remove('hidden');
    $('sessionRanking').innerHTML=totals.map((x,i)=>{
      const medal=i===0?'🥇':i===1?'🥈':i===2?'🥉':'#'+(i+1);
      return `<div class="row"><span>${medal} <strong>${esc(x[0])}</strong></span><strong class="score">${x[1]} Tournament XP</strong></div>`;
    }).join('')||'<div class="small">No standings yet.</div>';

    if(sessionDone && room.session_champion){
      const champScore=(room.session_scores||{})[room.session_champion]||0;
      $('sessionWinnerBox').innerHTML=`<div class="row session-champion-row"><span>👑 <strong>${esc(room.session_champion)}</strong></span><strong class="score">${champScore} Tournament XP</strong></div>`;
      $('battleAwards').innerHTML=(room.session_special_awards||[]).map(a=>`<div class="row"><span>${esc(a.award)} — <strong>${esc(a.name)}</strong></span><span class="score">${esc(a.reason||'')}</span></div>`).join('')||'<div class="small">No special tournament awards.</div>';
    }else{
      $('sessionWinnerBox').innerHTML='';
      $('battleAwards').innerHTML='';
    }

    // Tournament has cumulative standings only; the battle leaderboard is never displayed.
    $('leaderboardBtn').textContent=sessionDone?'🏆 View Final Tournament Standings':'🏟️ View Tournament Standings';
    $('leaderboardBtn').onclick=()=>document.getElementById('sessionStandingsSection').scrollIntoView({behavior:'smooth'});
  }else{
    $('sessionStandingsSection').classList.add('hidden');
    $('sessionWinnerSection').classList.add('hidden');
    $('specialAwardsSection').classList.remove('hidden');
    $('leaderboardSection').classList.remove('hidden');
    $('leaderboardTitle').textContent='🏆 Final Leaderboard';
    $('battleAwards').innerHTML=(room.battle_awards||[]).map(a=>`<div class="row"><span>${esc(a.award)} — <strong>${esc(a.name)}</strong></span><span class="score">${esc(a.reason||'')}</span></div>`).join('')||'<div class="small">No special awards this battle.</div>';
    $('resultRanking').innerHTML=visiblePlayers.map((p,i)=>{
      let medal=i===0?'🥇':i===1?'🥈':i===2?'🥉':'#'+(i+1);
      let acc=p.answered?Math.round((p.correct/p.answered)*100):0;
      return `<div class="row" style="flex-direction:column;align-items:flex-start"><div style="display:flex;justify-content:space-between;width:100%"><span>${medal} &nbsp;<strong>${esc(p.name)}</strong></span><strong class="score">${p.score} XP</strong></div><div class="muted" style="font-size:12px;margin-top:4px">Correct: ${p.correct}/${p.answered} • Acc: ${acc}% • Best Streak: 🔥 ${p.best_streak}</div></div>`;
    }).join('');
    $('leaderboardBtn').textContent='🏆 View Final Leaderboard';
    $('leaderboardBtn').onclick=()=>document.getElementById('leaderboardSection').scrollIntoView({behavior:'smooth'});
  }

  // Tournament dare is revealed only after the entire session. Normal battles keep theirs.
  if(room.dare&&room.dare_player&&(!isTournament||sessionDone)){
    $('dareplayer').textContent='😈 '+room.dare_player+' got last place!';
    $('dare').classList.remove('hidden');
    runDareRoulette(room.dares_list||[room.dare],room.dare);
  }else{
    $('dare').classList.add('hidden');
  }

  // No dashboard escape during a tournament until the final session result.
  const allowDashboard=!isTournament||sessionDone;
  $('dashboardResultBtn').classList.toggle('hidden',!allowDashboard);
  $('nextBattleBtn').classList.toggle('hidden', !isTournament || sessionDone || room.host.toLowerCase()!==playerName.toLowerCase());
  $('nextBattleBtn').textContent=`⚔️ Start Battle ${Math.min((room.session_battle||1)+1,room.session_battles||1)} / ${room.session_battles||1}`;
  show('result');
  if(isTournament && sessionDone){setTimeout(()=>showSessionChampionCelebration(room),180);}
}
function runDareRoulette(dares,finalDare){let el=$('daretext'),count=0,maxCycles=20;let int=setInterval(()=>{el.textContent=dares[Math.floor(Math.random()*dares.length)];count++;if(count>=maxCycles){clearInterval(int);el.textContent=finalDare;playSound('finish')}},100)}
</script>
<div id="bossBattlePanel" style="display:none" class="boss-battle-panel">
  <div class="boss-title">🐉 MULTIPLAYER BOSS BATTLE</div>
  <div id="bossName">StudyBattle Boss</div>
  <div class="boss-bar"><div id="bossHpBar" style="width:100%"></div></div>
  <div id="bossHpText">1000 / 1000 HP</div>
  <div id="bossDamageBoard"></div>
</div>
<script>
async function startBossBattle(code) {
  const r = await fetch('/api/boss_start', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({code})
  });
  return r.json();
}
async function attackBoss(code, name, fast=false) {
  const r = await fetch('/api/boss_attack', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({code, name, fast})
  });
  return r.json();
}
async function refreshBossState(code) {
  const r = await fetch('/api/boss_state', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({code})
  });
  const data = await r.json();
  if (!data.ok) return;
  const b = data.boss;
  const panel = document.getElementById('bossBattlePanel');
  if (panel) panel.style.display = b.active || b.defeated ? 'block' : 'none';
  const bar = document.getElementById('bossHpBar');
  if (bar) bar.style.width = ((b.hp / b.max_hp) * 100) + '%';
  const hp = document.getElementById('bossHpText');
  if (hp) hp.textContent = b.defeated ? '💥 BOSS DEFEATED!' : `${b.hp} / ${b.max_hp} HP`;
  const board = document.getElementById('bossDamageBoard');
  if (board) {
    board.innerHTML = Object.entries(b.damage || {})
      .sort((a,b)=>b[1]-a[1])
      .map(([n,d],i)=>`${i+1}. ${n} — ${d} damage`)
      .join('<br>');
  }
}
(function(){
  const drop=document.querySelector('.file-drop'), input=document.getElementById('pdf_file');
  if(!drop||!input)return;
  ['dragenter','dragover'].forEach(ev=>drop.addEventListener(ev,e=>{e.preventDefault();drop.style.borderColor='#67e8f9';drop.style.background='rgba(25,45,78,.7)';}));
  ['dragleave','drop'].forEach(ev=>drop.addEventListener(ev,e=>{e.preventDefault();drop.style.borderColor='';drop.style.background='';}));
  drop.addEventListener('drop',e=>{const f=e.dataTransfer.files&&e.dataTransfer.files[0];if(!f)return;if(!/\.pdf$/i.test(f.name)){toast('Please drop a PDF file.','error');return;}try{const dt=new DataTransfer();dt.items.add(f);input.files=dt.files;input.dispatchEvent(new Event('change',{bubbles:true}));}catch(_){}});
})();
</script>

</body></html>'''

load_progress()
threading.Thread(target=room_cleanup, daemon=True).start()

if __name__ == "__main__":
    print(f"StudyBattle V7 running on port {PORT}")
    print(f"Question bank: {len(get_all_questions())} questions ({len(uploaded_questions)} from PDFs)")
    app.run(host="0.0.0.0", port=PORT, debug=False, threaded=True)