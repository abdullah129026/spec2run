"use client";

import dynamic from "next/dynamic";
import { useEffect, useRef, useState } from "react";
import { Download, FileCode2, FileText, Github, RotateCcw } from "lucide-react";
import { downloadZip, generateCode } from "@/lib/api";
import { effectiveFiles, useSpec2RunStore } from "@/lib/store";
import GithubDialog from "./GithubDialog";

const Editor = dynamic(() => import("@monaco-editor/react"), { ssr: false });

function languageFor(path: string): string {
  if (path.endsWith(".py")) return "python";
  if (path.endsWith(".md")) return "markdown";
  if (path.endsWith(".env.example")) return "ini";
  return "plaintext";
}

function iconFor(path: string) {
  const cls = "shrink-0 text-zinc-500";
  return path.endsWith(".py") ? (
    <FileCode2 size={14} className={cls} />
  ) : (
    <FileText size={14} className={cls} />
  );
}

function repoSlug(spec: Record<string, unknown>): string {
  const title = (spec.info as Record<string, unknown> | undefined)?.title;
  const slug = String(title ?? "spec2run-service")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return slug || "spec2run-service";
}

export default function CodeTab() {
  const versions = useSpec2RunStore((s) => s.versions);
  const spec = useSpec2RunStore((s) => s.spec);
  const auth = useSpec2RunStore((s) => s.auth);
  const setVersionFiles = useSpec2RunStore((s) => s.setVersionFiles);
  const setEditedFile = useSpec2RunStore((s) => s.setEditedFile);
  const resetEdits = useSpec2RunStore((s) => s.resetEdits);

  const version = versions[versions.length - 1];
  const [path, setPath] = useState("app.py");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [retryTick, setRetryTick] = useState(0);
  const [zipBusy, setZipBusy] = useState(false);
  const [zipError, setZipError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [resetTick, setResetTick] = useState(0);
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!version || version.files || !spec || loading) return;
    setLoading(true);
    setError(null);
    generateCode(spec)
      .then((res) => {
        setVersionFiles(version.id, res.files);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "failed to load code"))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [version?.id, spec, retryTick]);

  useEffect(
    () => () => {
      if (saveTimer.current) clearTimeout(saveTimer.current);
    },
    [],
  );

  if (!version || !spec) return null;
  const files = effectiveFiles(version);

  function scheduleSave(filePath: string, value: string) {
    if (saveTimer.current) clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(() => {
      setEditedFile(version.id, filePath, value);
    }, 500);
  }

  async function onDownload() {
    if (zipBusy) return;
    setZipBusy(true);
    setZipError(null);
    try {
      await downloadZip(spec as Record<string, unknown>, auth);
    } catch (e) {
      setZipError(e instanceof Error ? e.message : "download failed");
    } finally {
      setZipBusy(false);
    }
  }

  const editedCount = Object.keys(version.edits).length;
  const fileNames = files ? Object.keys(files) : [];

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-zinc-800 px-4 py-2">
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs text-zinc-300">{path}</span>
          {version.edits[path] !== undefined && (
            <span
              className="rounded-full bg-amber-500/15 px-2 py-0.5 text-[10px] font-medium text-amber-300"
              title="Edited locally — the sandbox reboot in week 3 applies these"
            >
              modified
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {editedCount > 0 && (
            <button
              type="button"
              onClick={() => {
                resetEdits(version.id);
                setResetTick((t) => t + 1);
              }}
              className="flex items-center gap-1.5 rounded-md border border-zinc-700 px-2.5 py-1.5 text-xs text-zinc-400 hover:border-zinc-500 hover:text-zinc-200"
              title="Discard all local edits"
            >
              <RotateCcw size={12} />
              Reset
            </button>
          )}
          <button
            type="button"
            onClick={onDownload}
            disabled={zipBusy || !files}
            className="flex items-center gap-1.5 rounded-md border border-zinc-700 px-2.5 py-1.5 text-xs text-zinc-300 hover:border-zinc-500 hover:text-zinc-100 disabled:opacity-40"
          >
            <Download size={12} />
            {zipBusy ? "Zipping…" : "Download ZIP"}
          </button>
          <button
            type="button"
            onClick={() => setDialogOpen(true)}
            disabled={!files}
            className="flex items-center gap-1.5 rounded-md bg-indigo-600 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-indigo-500 disabled:opacity-40"
          >
            <Github size={12} />
            Push to GitHub
          </button>
        </div>
      </div>

      {zipError && (
        <p className="border-b border-zinc-800 bg-red-950/30 px-4 py-2 text-xs text-red-400">
          {zipError}
        </p>
      )}

      <div className="flex min-h-0 flex-1">
        <nav
          aria-label="Generated files"
          className="w-52 shrink-0 overflow-y-auto border-r border-zinc-800 p-2"
        >
          {loading &&
            fileNames.length === 0 &&
            ["app.py", "requirements.txt", "README.md", ".env.example"].map(
              (f) => (
                <div
                  key={f}
                  aria-hidden
                  className="mb-1 h-8 animate-pulse rounded bg-zinc-800/60"
                />
              ),
            )}
          {fileNames.map((f) => (
            <button
              key={f}
              type="button"
              onClick={() => setPath(f)}
              aria-current={path === f}
              className={`flex w-full items-center gap-2 rounded px-2 py-1.5 text-left font-mono text-xs ${
                path === f
                  ? "bg-zinc-800 text-zinc-100"
                  : "text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-200"
              }`}
            >
              {iconFor(f)}
              <span className="min-w-0 flex-1 truncate">{f}</span>
              {version.edits[f] !== undefined && (
                <span
                  className="h-1.5 w-1.5 shrink-0 rounded-full bg-amber-400"
                  title="modified"
                />
              )}
            </button>
          ))}
        </nav>

        <div className="min-w-0 flex-1">
          {loading && !files && (
            <div aria-hidden className="flex h-full flex-col gap-2 p-4">
              <div className="h-4 w-2/3 animate-pulse rounded bg-zinc-800" />
              <div className="h-4 w-1/2 animate-pulse rounded bg-zinc-800" />
              <div className="h-4 w-3/4 animate-pulse rounded bg-zinc-800" />
              <div className="h-4 w-1/3 animate-pulse rounded bg-zinc-800" />
            </div>
          )}
          {error && (
            <div className="flex h-full items-center justify-center p-8">
              <div className="max-w-sm rounded-md border border-red-900/60 bg-red-950/30 p-4 text-center">
                <p className="text-sm font-medium text-red-300">
                  Code generation failed
                </p>
                <p className="mt-1 text-xs leading-relaxed text-red-400">{error}</p>
                <button
                  type="button"
                  onClick={() => {
                    setError(null);
                    setRetryTick((t) => t + 1);
                  }}
                  className="mt-3 text-xs font-medium text-red-300 underline underline-offset-2 hover:text-red-200"
                >
                  Retry
                </button>
              </div>
            </div>
          )}
          {files && files[path] !== undefined && (
            <Editor
              key={`${path}-${resetTick}`}
              height="100%"
              language={languageFor(path)}
              defaultValue={files[path]}
              onChange={(v) => scheduleSave(path, v ?? "")}
              theme="vs-dark"
              options={{
                minimap: { enabled: false },
                fontSize: 13,
                fontFamily: "'JetBrains Mono', ui-monospace, Menlo, monospace",
                padding: { top: 12 },
                scrollBeyondLastLine: false,
                renderLineHighlight: "line",
              }}
              loading={
                <div aria-hidden className="h-full animate-pulse bg-[#101013]" />
              }
            />
          )}
        </div>
      </div>

      {dialogOpen && (
        <GithubDialog
          spec={spec}
          auth={auth}
          defaultRepo={repoSlug(spec)}
          onClose={() => setDialogOpen(false)}
        />
      )}
    </div>
  );
}
