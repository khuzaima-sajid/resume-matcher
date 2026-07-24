"use client";

import { useRef, useState } from "react";
import ScoreGauge from "@/components/ScoreGauge";

type MatchResult = {
  match_score: number;
  missing_keywords: string[];
  suggestions: string[];
};

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [jobDescription, setJobDescription] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<MatchResult | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = (f: File | undefined | null) => {
    if (!f) return;
    const okType = f.name.endsWith(".pdf") || f.name.endsWith(".docx");
    if (!okType) {
      setError("Please upload a PDF or DOCX file.");
      return;
    }
    setError(null);
    setFile(f);
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    handleFile(e.dataTransfer.files?.[0]);
  };

  const onSubmit = async () => {
    if (!file) {
      setError("Please upload your resume first.");
      return;
    }
    if (!jobDescription.trim()) {
      setError("Please paste the job description.");
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const formData = new FormData();
      formData.append("resume", file);
      formData.append("job_description", jobDescription);

      const res = await fetch(`${API_URL}/api/analyze`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Something went wrong." }));
        throw new Error(err.detail || "Something went wrong.");
      }

      const data: MatchResult = await res.json();
      setResult(data);
    } catch (e: any) {
      setError(e.message || "Failed to analyze. Is the backend running?");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="mx-auto max-w-4xl px-6 py-14">
      {/* Header */}
      <div className="mb-10 text-center animate-fade-in">
        <div className="mb-3 inline-flex items-center gap-2 rounded-full bg-brand-100 px-4 py-1 text-sm font-medium text-brand-700">
          ✨ AI-powered resume analysis
        </div>
        <h1 className="text-4xl font-bold tracking-tight text-slate-900 sm:text-5xl">
          Resume<span className="text-brand-500">Match</span>
        </h1>
        <p className="mx-auto mt-3 max-w-xl text-slate-500">
          Upload your resume and a job description. Get an instant match score,
          missing keywords, and concrete rewrite suggestions.
        </p>
      </div>

      {/* Input card */}
      <div className="grid gap-6 rounded-2xl border border-slate-200 bg-white/70 p-6 shadow-sm backdrop-blur sm:p-8 animate-fade-in">
        <div className="grid gap-6 sm:grid-cols-2">
          {/* Resume upload */}
          <div>
            <label className="mb-2 block text-sm font-semibold text-slate-700">
              1. Upload your resume
            </label>
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setDragActive(true);
              }}
              onDragLeave={() => setDragActive(false)}
              onDrop={onDrop}
              onClick={() => inputRef.current?.click()}
              className={`flex h-40 cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed p-4 text-center transition ${
                dragActive
                  ? "border-brand-500 bg-brand-50"
                  : "border-slate-300 hover:border-brand-400 hover:bg-brand-50/50"
              }`}
            >
              <input
                ref={inputRef}
                type="file"
                accept=".pdf,.docx"
                className="hidden"
                onChange={(e) => handleFile(e.target.files?.[0])}
              />
              {file ? (
                <>
                  <span className="text-2xl">📄</span>
                  <p className="mt-1 truncate max-w-full text-sm font-medium text-slate-700">
                    {file.name}
                  </p>
                  <p className="text-xs text-brand-600">Click to replace</p>
                </>
              ) : (
                <>
                  <span className="text-2xl">⬆️</span>
                  <p className="mt-1 text-sm font-medium text-slate-600">
                    Drop file or click to browse
                  </p>
                  <p className="text-xs text-slate-400">PDF or DOCX</p>
                </>
              )}
            </div>
          </div>

          {/* Job description */}
          <div>
            <label className="mb-2 block text-sm font-semibold text-slate-700">
              2. Paste the job description
            </label>
            <textarea
              value={jobDescription}
              onChange={(e) => setJobDescription(e.target.value)}
              placeholder="Paste the full job description here..."
              className="h-40 w-full resize-none rounded-xl border border-slate-300 p-3 text-sm outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
            />
          </div>
        </div>

        {error && (
          <p className="rounded-lg bg-red-50 px-4 py-2 text-sm text-red-600">{error}</p>
        )}

        <button
          onClick={onSubmit}
          disabled={loading}
          className="w-full rounded-xl bg-brand-500 px-6 py-3 font-semibold text-white shadow-sm transition hover:bg-brand-600 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {loading ? "Analyzing..." : "Analyze Match"}
        </button>
      </div>

      {/* Results */}
      {result && (
        <div className="mt-8 grid gap-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8 animate-fade-in">
          <div className="grid gap-8 sm:grid-cols-[auto,1fr] sm:items-center">
            <ScoreGauge score={result.match_score} />
            <div>
              <h2 className="text-lg font-semibold text-slate-800">Missing Keywords</h2>
              <div className="mt-2 flex flex-wrap gap-2">
                {result.missing_keywords.length === 0 ? (
                  <span className="text-sm text-slate-400">None — great coverage!</span>
                ) : (
                  result.missing_keywords.map((kw) => (
                    <span
                      key={kw}
                      className="rounded-full bg-amber-50 px-3 py-1 text-xs font-medium text-amber-700 ring-1 ring-inset ring-amber-200"
                    >
                      {kw}
                    </span>
                  ))
                )}
              </div>
            </div>
          </div>

          <div>
            <h2 className="mb-2 text-lg font-semibold text-slate-800">
              Rewrite Suggestions
            </h2>
            <ul className="grid gap-2">
              {result.suggestions.map((s, i) => (
                <li
                  key={i}
                  className="flex gap-3 rounded-lg bg-slate-50 p-3 text-sm text-slate-700"
                >
                  <span className="mt-0.5 text-brand-500">✓</span>
                  <span>{s}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      <p className="mt-10 text-center text-xs text-slate-400">
        Built with Next.js, FastAPI & Claude
      </p>
    </main>
  );
}
