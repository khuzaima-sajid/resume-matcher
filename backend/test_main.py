import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent))
import main


client = TestClient(main.app)


def _resume_file():
    return {
        "resume": (
            "resume.docx",
            b"dummy-content",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    }


class AnalyzeEndpointTests(unittest.TestCase):
    def test_analyze_rejects_empty_job_description(self):
        response = client.post(
            "/api/analyze",
            files=_resume_file(),
            data={"job_description": "   "},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Job description cannot be empty.")

    def test_analyze_requires_anthropic_api_key(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}):
            with patch.object(main, "extract_resume_text", return_value="resume text"):
                response = client.post(
                    "/api/analyze",
                    files=_resume_file(),
                    data={"job_description": "Python backend engineer role"},
                )
        self.assertEqual(response.status_code, 500)
        self.assertIn("ANTHROPIC_API_KEY", response.json()["detail"])

    def test_analyze_handles_malformed_llm_response_schema(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch.object(main, "extract_resume_text", return_value="resume text"):
                with patch.object(main, "call_llm_for_json", return_value={"match_score": 90}):
                    response = client.post(
                        "/api/analyze",
                        files=_resume_file(),
                        data={"job_description": "Python backend engineer role"},
                    )
        self.assertEqual(response.status_code, 502)
        self.assertEqual(
            response.json()["detail"],
            "LLM response JSON did not match the expected schema.",
        )

    def test_analyze_success_with_valid_shape(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch.object(main, "extract_resume_text", return_value="resume text"):
                with patch.object(
                    main,
                    "call_llm_for_json",
                    return_value={
                        "match_score": 82,
                        "missing_keywords": ["kubernetes"],
                        "suggestions": ["Add Kubernetes production experience details."],
                    },
                ):
                    response = client.post(
                        "/api/analyze",
                        files=_resume_file(),
                        data={"job_description": "Python backend engineer role"},
                    )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["match_score"], 82)


if __name__ == "__main__":
    unittest.main()
