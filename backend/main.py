"""
Resume vs Job Description Matcher — Backend
--------------------------------------------
FastAPI service that:
  1. Accepts a resume file (PDF/DOCX) + a job description (text)
  2. Extracts resume text
  3. Sends both to an LLM (Claude) with a prompt that forces JSON output
  4. Validates the JSON, retries once if the model returns malformed JSON
  5. Returns { match_score, missing_keywords, suggestions }
"""

import io
import json
import os

from anthropic import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    Anthropic,
    RateLimitError,
)
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ValidationError
from pypdf import PdfReader
from docx import Document

load_dotenv()

app = FastAPI(title="Resume Matcher API")

# ---------------------------------------------------------------------------
# CORS — allows the Next.js frontend (localhost:3000 in dev) to call this API
# ---------------------------------------------------------------------------
origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "30"))
client = Anthropic(
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    timeout=LLM_TIMEOUT_SECONDS,
)
MODEL_NAME = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5")


# ---------------------------------------------------------------------------
# Response schema
# ---------------------------------------------------------------------------
class MatchResult(BaseModel):
    match_score: int = Field(ge=0, le=100)
    missing_keywords: list[str]
    suggestions: list[str]


# ---------------------------------------------------------------------------
# Text extraction helpers
# ---------------------------------------------------------------------------
def extract_pdf_text(file_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(file_bytes))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    if not text.strip():
        raise HTTPException(
            status_code=422,
            detail="Couldn't read text from this PDF. It may be a scanned "
            "image — try a text-based PDF or a DOCX file instead.",
        )
    return text


def extract_docx_text(file_bytes: bytes) -> str:
    doc = Document(io.BytesIO(file_bytes))
    return "\n".join(p.text for p in doc.paragraphs)


def extract_resume_text(filename: str, file_bytes: bytes) -> str:
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return extract_pdf_text(file_bytes)
    if lower.endswith(".docx"):
        return extract_docx_text(file_bytes)
    raise HTTPException(status_code=400, detail="Only PDF or DOCX files are supported.")


# ---------------------------------------------------------------------------
# Prompt template — forces strict JSON output
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are an expert technical recruiter and ATS (Applicant \
Tracking System) analyst. Compare a candidate's resume against a job \
description and evaluate the match.

You MUST respond with ONLY valid JSON — no markdown, no code fences, no \
commentary before or after. The JSON must match this exact schema:

{
  "match_score": <integer 0-100, how well the resume matches the job>,
  "missing_keywords": [<important skills/keywords from the JD absent in the resume>],
  "suggestions": [<specific, actionable rewrite suggestions to improve the match>]
}

Scoring guide:
- 90-100: Excellent match, nearly all key requirements covered
- 70-89: Strong match, minor gaps
- 50-69: Moderate match, several important gaps
- 0-49: Weak match, major gaps

Keep missing_keywords focused on real skills/tools/qualifications (5-12 items). \
Keep suggestions concrete and specific to this resume (4-8 items)."""


def build_user_prompt(resume_text: str, job_description: str) -> str:
    return f"""JOB DESCRIPTION:
{job_description}

---

RESUME:
{resume_text}

---

Analyze the match and respond with the JSON object only."""


def call_llm_for_json(resume_text: str, job_description: str) -> dict:
    """Call the LLM and parse JSON, with one retry that explicitly asks the
    model to fix its own output if it wasn't valid JSON the first time."""

    def _call(extra_instruction: str = "") -> str:
        try:
            response = client.messages.create(
                model=MODEL_NAME,
                system=SYSTEM_PROMPT + extra_instruction,
                max_tokens=1500,
                messages=[
                    {"role": "user", "content": build_user_prompt(resume_text, job_description)}
                ],
            )
            text_parts = [
                block.text for block in response.content if getattr(block, "type", None) == "text"
            ]
            return "".join(text_parts).strip()
        except RateLimitError:
            raise HTTPException(
                status_code=429,
                detail="Rate limit reached from the LLM provider. Please retry shortly.",
            )
        except APITimeoutError:
            raise HTTPException(
                status_code=504,
                detail=(
                    "LLM request timed out. Try again or increase LLM_TIMEOUT_SECONDS in "
                    "backend/.env."
                ),
            )
        except APIConnectionError:
            raise HTTPException(
                status_code=503,
                detail="Unable to reach the LLM provider. Please try again.",
            )
        except APIStatusError as e:
            raise HTTPException(
                status_code=502,
                detail=f"LLM provider returned an error (status {e.status_code}).",
            )
        except Exception as e:
            raise HTTPException(
                status_code=502,
                detail=f"Unexpected LLM provider error: {type(e).__name__}",
            )

    raw = _call()
    try:
        return _parse_llm_json(raw)
    except json.JSONDecodeError:
        # Retry once, telling the model exactly what went wrong
        raw_retry = _call(
            "\n\nIMPORTANT: Your previous response was not valid JSON. "
            "Respond with ONLY the raw JSON object, nothing else."
        )
        try:
            return _parse_llm_json(raw_retry)
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=502,
                detail=f"LLM did not return valid JSON after retry: {e}",
            )
        except ValueError as e:
            raise HTTPException(status_code=502, detail=f"Malformed LLM response: {e}")
    except ValueError as e:
        raise HTTPException(status_code=502, detail=f"Malformed LLM response: {e}")


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return text.strip()


def _parse_llm_json(raw_text: str) -> dict:
    parsed = json.loads(_strip_code_fences(raw_text))
    if not isinstance(parsed, dict):
        raise ValueError("Response must be a JSON object.")
    required_keys = {"match_score", "missing_keywords", "suggestions"}
    missing_keys = required_keys - set(parsed.keys())
    if missing_keys:
        raise ValueError(f"Missing required keys: {', '.join(sorted(missing_keys))}")
    return parsed


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/analyze", response_model=MatchResult)
async def analyze(
    resume: UploadFile = File(...),
    job_description: str = Form(...),
):
    if not job_description.strip():
        raise HTTPException(status_code=400, detail="Job description cannot be empty.")

    file_bytes = await resume.read()
    resume_text = extract_resume_text(resume.filename, file_bytes)

    if not os.getenv("ANTHROPIC_API_KEY"):
        raise HTTPException(
            status_code=500,
            detail="Server is missing ANTHROPIC_API_KEY. Add it to backend/.env",
        )

    result = call_llm_for_json(resume_text, job_description)

    # Validate against schema before returning (raises 500 if the model's
    # JSON is well-formed but doesn't match our expected shape)
    try:
        validated = MatchResult(**result)
        return validated
    except ValidationError:
        raise HTTPException(
            status_code=502,
            detail="LLM response JSON did not match the expected schema.",
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
