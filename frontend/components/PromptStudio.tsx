"use client";

import { useEffect, useState } from "react";
import { Check, Upload } from "lucide-react";
import { backendAlive, generateSpec, patchSpec, refineSpec } from "@/lib/api";
import { useSpec2RunStore } from "@/lib/store";
import ImportDialog from "./ImportDialog";

const EXAMPLES = [
  "Create an API for a bookstore with books, authors, and orders. Books have title and price. I need JWT auth.",
  "A todo API with lists and items. Items have a title and a done flag.",
  "A blog API with posts and comments. Posts have title, body, and tags.",
];

function friendlyError(e: unknown): string {
  const msg = e instanceof Error ? e.message : "generation failed";
  if (msg.includes("503") || msg.includes("GROQ"))
    return "The model key isn't configured on the backend yet, so generation can't run. Check SPEC2RUN_GROQ_API_KEY and retry.";
  if (msg.includes("422"))
    return `The spec engine couldn't build a usable spec: ${msg}. Try a more concrete description.`;
  if (msg.includes("Failed to fetch"))
    return "Couldn't reach the backend. Make sure the API is running and try again.";
  return msg;
}

export default function PromptStudio() {
  const prompt = useSpec2RunStore((s) => s.prompt);
  const setPrompt = useSpec2RunStore((s) => s.setPrompt);
  const status = useSpec2RunStore((s) => s.status);
  const setStatus = useSpec2RunStore((s) => s.setStatus);
  const error = useSpec2RunStore((s) => s.error);
  const setError = useSpec2RunStore((s) => s.setError);
  const questions = useSpec2RunStore((s) => s.questions);
  const setQuestions = useSpec2RunStore((s) => s.setQuestions);
  const answers = useSpec2RunStore((s) => s.answers);
  const setAnswers = useSpec2RunStore((s) => s.setAnswers);
  const auth = useSpec2RunStore((s) => s.auth);
  const setAuth = useSpec2RunStore((s) => s.setAuth);
  const spec = useSpec2RunStore((s) => s.spec);
  const addVersion = useSpec2RunStore((s) => s.addVersion);
  const resetAll = useSpec2RunStore((s) => s.resetAll);

  const [importOpen, setImportOpen] = useState(false);
  const busy = status === "loading";
  // A spec already exists: the textarea edits it ("add reviews to books").
  const patchMode = spec !== null && status === "done";

  // Sandbox pill reflects the real backend, not a hardcoded label.
  const [sandboxLive, setSandboxLive] = useState<boolean | null>(null);
  useEffect(() => {
    let on = true;
    const probe = () => {
      backendAlive().then((v) => {
        if (on) setSandboxLive(v);
      });
    };
    probe();
    // The backend sleeps on a free Render tier and can take 30-60s to
    // cold-start; a one-shot probe would leave the pill stuck on
    // "offline" for the whole visit.
    const id = setInterval(probe, 60000);
    return () => {
      on = false;
      clearInterval(id);
    };
  }, []);

  function handleResult(res: Record<string, unknown>, label: string) {
    if (res.needs_clarification) {
      const qs = Array.isArray(res.questions)
        ? res.questions.filter((q): q is string => typeof q === "string")
        : [];
      setQuestions(qs);
      setStatus("idle");
    } else {
      setPrompt("");
      addVersion(label, res);
      setStatus("done");
    }
  }

  async function generate() {
    const text = prompt.trim();
    if (!text || busy) return;
    setStatus("loading");
    setError(null);
    setQuestions([]);
    try {
      if (patchMode && spec) {
        handleResult(await patchSpec(spec, text, auth), text);
      } else {
        handleResult(
          await generateSpec(text, {
            auth,
            database: "postgres",
            language: "python",
          }),
          text,
        );
      }
    } catch (e) {
      setError(friendlyError(e));
      setStatus("error");
    }
  }

  async function sendAnswers() {
    if (busy) return;
    setStatus("loading");
    setError(null);
    try {
      let res: Record<string, unknown>;
      if (patchMode && spec) {
        const enriched =
          prompt.trim() +
          "\n\nThe user answered these clarifying questions:\n" +
          questions
            .map((q, i) => `- ${q.trim()}: ${(answers[i] ?? "").trim()}`)
            .filter((line) => line.length > 4)
            .join("\n");
        res = await patchSpec(spec, enriched, auth);
      } else {
        res = await refineSpec(prompt.trim(), questions, answers, auth);
      }
      setQuestions([]);
      handleResult(res, prompt.trim());
    } catch (e) {
      setError(friendlyError(e));
      setStatus("error");
    }
  }

  return (
    <div className="flex h-full flex-col gap-4 overflow-y-auto p-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold">Spec2Run</h1>
          <p className="mt-1 text-sm text-zinc-400">
            {patchMode
              ? "Describe a change to the current API."
              : "Describe the API you want in plain English."}
          </p>
        </div>
        <span
          className="flex shrink-0 items-center gap-1.5 rounded-full border border-zinc-800 px-2.5 py-1 text-[11px] text-zinc-500"
          title="Whether the backend's live sandbox is reachable right now"
        >
          <span
            className={`h-1.5 w-1.5 rounded-full ${
              sandboxLive ? "bg-emerald-400" : "bg-zinc-600"
            }`}
          />
          {sandboxLive === null
            ? "checking sandbox"
            : sandboxLive
              ? "sandbox live"
              : "sandbox offline"}
        </span>
      </div>

      <textarea
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            generate();
          }
        }}
        placeholder={
          patchMode
            ? "Add reviews to books…"
            : "Create an API for a bookstore…"
        }
        rows={6}
        disabled={busy}
        aria-label="API description"
        className="w-full rounded-md border border-zinc-800 bg-zinc-900 p-3 text-sm outline-none placeholder:text-zinc-600 focus:border-indigo-600 disabled:opacity-60"
      />

      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={() => setAuth(!auth)}
          aria-pressed={auth}
          className={`flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs ${
            auth
              ? "border-indigo-500 bg-indigo-600/15 text-indigo-300"
              : "border-zinc-700 text-zinc-400 hover:border-zinc-500 hover:text-zinc-200"
          }`}
        >
          {auth && <Check size={12} />}
          JWT auth
        </button>
        <span
          className="rounded-full border border-zinc-800 px-3 py-1 text-xs text-zinc-500"
          title="Postgres is the only database for now"
        >
          Postgres
        </span>
        <span
          className="rounded-full border border-zinc-800 px-3 py-1 text-xs text-zinc-500"
          title="FastAPI is the only stack for now"
        >
          Python
        </span>
      </div>

      <button
        type="button"
        onClick={generate}
        disabled={!prompt.trim() || busy}
        className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-40"
      >
        {busy ? "Generating…" : patchMode ? "Update API" : "Generate API"}
      </button>

      {patchMode && (
        <button
          type="button"
          onClick={resetAll}
          className="self-start text-xs text-zinc-500 underline underline-offset-2 hover:text-zinc-300"
        >
          Start a new API instead
        </button>
      )}

      {busy && (
        <div aria-hidden className="flex flex-col gap-2">
          <div className="h-4 animate-pulse rounded bg-zinc-800" />
          <div className="h-4 w-5/6 animate-pulse rounded bg-zinc-800" />
          <div className="h-4 w-2/3 animate-pulse rounded bg-zinc-800" />
        </div>
      )}

      {status === "error" && error && (
        <div className="rounded-md border border-red-900/60 bg-red-950/30 p-3">
          <p className="text-xs leading-relaxed text-red-400">{error}</p>
          <button
            type="button"
            onClick={generate}
            className="mt-2 text-xs font-medium text-red-300 underline underline-offset-2 hover:text-red-200"
          >
            Retry
          </button>
        </div>
      )}

      {questions.length > 0 && (
        <div className="rounded-md border border-amber-900/60 bg-amber-950/20 p-3">
          <p className="mb-2 text-xs font-medium text-amber-300">
            The spec engine needs a little more detail:
          </p>
          <div className="flex flex-col gap-2">
            {questions.map((q, i) => (
              <label key={i} className="block">
                <span className="mb-1 block text-xs text-zinc-400">{q}</span>
                <input
                  value={answers[i] ?? ""}
                  onChange={(e) => {
                    const next = [...answers];
                    next[i] = e.target.value;
                    setAnswers(next);
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") sendAnswers();
                  }}
                  className="w-full rounded-md border border-zinc-800 bg-zinc-900 p-2 text-xs outline-none focus:border-indigo-600"
                />
              </label>
            ))}
          </div>
          <button
            type="button"
            onClick={sendAnswers}
            disabled={busy || answers.every((a) => !a.trim())}
            className="mt-3 rounded-md bg-indigo-600 px-3 py-1.5 text-xs font-medium hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Send answers
          </button>
        </div>
      )}

      <div>
        <p className="mb-2 text-xs uppercase tracking-wide text-zinc-500">
          Try an example
        </p>
        <div className="flex flex-col gap-2">
          {EXAMPLES.map((ex) => (
            <button
              key={ex}
              type="button"
              onClick={() => setPrompt(ex)}
              className="rounded-md border border-zinc-800 p-3 text-left text-xs leading-relaxed text-zinc-400 hover:border-zinc-600 hover:text-zinc-200"
            >
              {ex}
            </button>
          ))}
        </div>
      </div>

      <button
        type="button"
        onClick={() => setImportOpen(true)}
        className="flex items-center justify-center gap-2 rounded-md border border-zinc-800 px-4 py-2 text-xs text-zinc-400 hover:border-zinc-600 hover:text-zinc-200"
      >
        <Upload size={14} />
        or import an OpenAPI file/URL
      </button>

      {importOpen && <ImportDialog onClose={() => setImportOpen(false)} />}
    </div>
  );
}
