"use client";

import { useEffect, useState } from "react";
import { pushToGithub } from "@/lib/api";

interface Props {
  spec: Record<string, unknown>;
  auth: boolean;
  defaultRepo: string;
  onClose: () => void;
}

export default function GithubDialog({ spec, auth, defaultRepo, onClose }: Props) {
  const [repo, setRepo] = useState(defaultRepo);
  const [token, setToken] = useState("");
  const [description, setDescription] = useState("");
  const [isPrivate, setIsPrivate] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{ repo: string; url: string } | null>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!repo.trim() || !token.trim() || busy) return;
    setBusy(true);
    setError(null);
    try {
      const r = await pushToGithub(
        spec,
        token.trim(),
        repo.trim(),
        description.trim(),
        isPrivate,
        auth,
      );
      setResult(r);
      setToken(""); // don't linger in memory longer than the request
    } catch (err) {
      setError(err instanceof Error ? err.message : "push failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="Push to GitHub"
    >
      <div
        className="w-full max-w-md rounded-lg border border-zinc-800 bg-[#101013] p-5"
        onClick={(e) => e.stopPropagation()}
      >
        {result ? (
          <div>
            <p className="text-sm font-medium text-zinc-100">Pushed to GitHub</p>
            <p className="mt-2 font-mono text-xs text-zinc-400">{result.repo}</p>
            <a
              href={result.url}
              target="_blank"
              rel="noreferrer"
              className="mt-3 inline-block rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500"
            >
              Open repository
            </a>
            <button
              type="button"
              onClick={onClose}
              className="ml-2 rounded-md border border-zinc-700 px-4 py-2 text-sm text-zinc-300 hover:border-zinc-500"
            >
              Close
            </button>
          </div>
        ) : (
          <form onSubmit={submit}>
            <p className="text-sm font-medium text-zinc-100">Push to GitHub</p>
            <p className="mt-1 text-xs leading-relaxed text-zinc-500">
              Creates a repo under your account and pushes the generated
              service. Your token is sent to the backend for this request
              only — it is never stored or logged.
            </p>

            <label className="mt-4 block">
              <span className="mb-1 block text-xs text-zinc-400">
                Repository name
              </span>
              <input
                value={repo}
                onChange={(e) => setRepo(e.target.value)}
                pattern="[A-Za-z0-9._-]+"
                title="Letters, numbers, dots, dashes, underscores"
                required
                maxLength={100}
                autoFocus
                className="w-full rounded-md border border-zinc-800 bg-zinc-900 p-2 font-mono text-xs outline-none focus:border-indigo-600"
              />
            </label>

            <label className="mt-3 block">
              <span className="mb-1 block text-xs text-zinc-400">
                Personal access token{" "}
                <span className="text-zinc-600">(classic, repo scope)</span>
              </span>
              <input
                type="password"
                value={token}
                onChange={(e) => setToken(e.target.value)}
                required
                autoComplete="off"
                placeholder="ghp_…"
                className="w-full rounded-md border border-zinc-800 bg-zinc-900 p-2 font-mono text-xs outline-none focus:border-indigo-600"
              />
            </label>

            <label className="mt-3 block">
              <span className="mb-1 block text-xs text-zinc-400">
                Description <span className="text-zinc-600">(optional)</span>
              </span>
              <input
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                maxLength={300}
                className="w-full rounded-md border border-zinc-800 bg-zinc-900 p-2 text-xs outline-none focus:border-indigo-600"
              />
            </label>

            <label className="mt-3 flex cursor-pointer items-center gap-2 text-xs text-zinc-400">
              <input
                type="checkbox"
                checked={isPrivate}
                onChange={(e) => setIsPrivate(e.target.checked)}
                className="accent-indigo-600"
              />
              Private repository
            </label>

            {error && (
              <p className="mt-3 rounded-md border border-red-900/60 bg-red-950/30 p-2 text-xs leading-relaxed text-red-400">
                {error}
              </p>
            )}

            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                onClick={onClose}
                className="rounded-md border border-zinc-700 px-4 py-2 text-sm text-zinc-300 hover:border-zinc-500"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={busy || !repo.trim() || !token.trim()}
                className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-40"
              >
                {busy ? "Pushing…" : "Push"}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
