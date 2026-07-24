# ResumeMatch

Compares a resume against a job description, returns a match score (0–100),
flags missing keywords, and gives concrete rewrite suggestions — powered by
an LLM with strict JSON output.

## Tech Stack

| Layer     | Technology                            |
|-----------|-------------------------------------- |
| Frontend  | Next.js 14 (App Router) + Tailwind CSS|
| Backend   | FastAPI (Python)                      |
| LLM       | Claude(Code)+Gemini (Anthropic API)   |
| File parsing | pypdf, python-docx                 |

## Features

- Upload a resume as PDF or DOCX (text extracted automatically)
- Paste a job description
- LLM comparison returns strict JSON: `match_score`, `missing_keywords`, `suggestions`
- JSON validation with automatic retry if the model's first response is malformed
- Clean, responsive UI with animated score gauge

## Project Structure

```
resume-matcher/
├── backend/          # FastAPI app
│   ├── main.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/          # Next.js app
│   ├── app/
│   ├── components/
│   └── .env.local.example
└── README.md
```

## Setup

### 1. Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and paste your ANTHROPIC_API_KEY
uvicorn main:app --reload
```

Backend runs at `http://localhost:8000`. Health check: `GET /api/health`.

### 2. Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

Frontend runs at `http://localhost:3000`.

### 3. Get an Anthropic API key

Create one at [console.anthropic.com](https://console.anthropic.com/settings/keys)
and paste it into `backend/.env` as `ANTHROPIC_API_KEY`.

## How it Works

1. User uploads a resume (PDF/DOCX) and pastes a job description in the UI.
2. The frontend sends both to `POST /api/analyze` on the FastAPI backend.
3. The backend extracts resume text, builds a prompt that forces the LLM
   to return **only JSON**, and calls the Claude API.
4. If the model's response isn't valid JSON, the backend retries once with
   an explicit correction instruction.
5. The validated JSON (`match_score`, `missing_keywords`, `suggestions`) is
   returned to the frontend and rendered.


## Common Blockers & Fixes

- **CORS errors** → `CORSMiddleware` is already configured in `backend/main.py`; make sure `ALLOWED_ORIGINS` in `.env` matches your frontend URL.
- **Scanned PDFs fail to extract text** → currently unsupported; use a text-based PDF or DOCX. (OCR fallback with Tesseract can be added as a future improvement.)
- **LLM returns prose instead of JSON** → the system prompt forces JSON, and the backend automatically retries once if parsing fails.
- **API keys exposed** → keys are loaded from `.env` files, which are excluded via `.gitignore`. Never commit `.env`.

## License

MIT
