"use client";

import { useEffect, useMemo, useState } from "react";
import { FileDiff } from "lucide-react";
import { diffVersions, type DiffResult } from "@/lib/api";
import { useSpec2RunStore } from "@/lib/store";

function compact(v: unknown): string {
  const s = JSON.stringify(v);
  return s === undefined ? "—" : s.length > 120 ? s.slice(0, 120) + "…" : s;
}

function countDiff(diff: string): { added: number; removed: number } {
  let added = 0;
  let removed = 0;
  for (const line of diff.split("\n")) {
    if (line.startsWith("+++") || line.startsWith("---")) continue;
    if (line.startsWith("+")) added++;
    else if (line.startsWith("-")) removed++;
  }
  return { added, removed };
}

function DiffLine({ line }: { line: string }) {
  let cls = "text-zinc-400";
  if (line.startsWith("+++") || line.startsWith("---")) cls = "text-zinc-500";
  else if (line.startsWith("@@")) cls = "text-indigo-300";
  else if (line.startsWith("+")) cls = "bg-emerald-500/10 text-emerald-300";
  else if (line.startsWith("-")) cls = "bg-red-500/10 text-red-300";
  return (
    <div className={`whitespace-pre px-4 ${cls}`}>
      <span className="select-none opacity-40">
        {line.startsWith("+") && !line.startsWith("+++")
          ? "+"
          : line.startsWith("-") && !line.startsWith("---")
            ? "−"
            : " "}
      </span>{" "}
      {line.replace(/^[+-]/, "")}
    </div>
  );
}

export default function DiffTab() {
  const versions = useSpec2RunStore((s) => s.versions);
  const latest = versions[versions.length - 1];
  const [baseIdx, setBaseIdx] = useState(versions.length - 2);
  const [diff, setDiff] = useState<DiffResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [retryTick, setRetryTick] = useState(0);

  const base = versions[baseIdx];

  useEffect(() => {
    if (!base || !latest || base.id === latest.id) return;
    setLoading(true);
    setError(null);
    setDiff(null);
    diffVersions(base.spec, latest.spec)
      .then(setDiff)
      .catch((e) =>
        setError(e instanceof Error ? e.message : "failed to compute the diff"),
      )
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [base?.id, latest?.id, retryTick]);

  const fileEntries = useMemo(
    () =>
      diff
        ? Object.entries(diff.file_diffs).map(([path, d]) => ({
            path,
            diff: d,
            ...countDiff(d),
          }))
        : [],
    [diff],
  );

  if (versions.length < 2) return null;

  const empty =
    diff &&
    diff.spec_changes.length === 0 &&
    Object.keys(diff.file_diffs).length === 0;

  return (
    <div className="flex h-full flex-col overflow-y-auto">
      <div className="flex items-center gap-2 border-b border-zinc-800 px-4 py-2.5">
        <span className="text-xs text-zinc-500">Compare</span>
        <select
          value={baseIdx}
          onChange={(e) => setBaseIdx(Number(e.target.value))}
          aria-label="Base version"
          className="rounded-md border border-zinc-800 bg-zinc-900 px-2 py-1 font-mono text-xs text-zinc-200 outline-none focus:border-indigo-600"
        >
          {versions.slice(0, -1).map((v, i) => (
            <option key={v.id} value={i}>
              v{v.id} — {v.label}
            </option>
          ))}
        </select>
        <span className="text-xs text-zinc-600">←</span>
        <span className="rounded-md border border-indigo-500/40 bg-indigo-600/15 px-2 py-1 font-mono text-xs text-indigo-300">
          v{latest.id} — {latest.label}
        </span>
      </div>

      {loading && (
        <div aria-hidden className="flex flex-col gap-3 p-6">
          <div className="h-6 w-1/4 animate-pulse rounded bg-zinc-800" />
          <div className="h-24 animate-pulse rounded bg-zinc-800" />
          <div className="h-24 animate-pulse rounded bg-zinc-800" />
        </div>
      )}

      {error && (
        <div className="flex flex-1 items-center justify-center p-8">
          <div className="max-w-sm rounded-md border border-red-900/60 bg-red-950/30 p-4 text-center">
            <p className="text-sm font-medium text-red-300">Diff failed</p>
            <p className="mt-1 text-xs leading-relaxed text-red-400">{error}</p>
            <button
              type="button"
              onClick={() => setRetryTick((t) => t + 1)}
              className="mt-3 text-xs font-medium text-red-300 underline underline-offset-2 hover:text-red-200"
            >
              Retry
            </button>
          </div>
        </div>
      )}

      {!loading && !error && empty && (
        <div className="flex flex-1 items-center justify-center p-8">
          <p className="max-w-sm text-center text-sm text-zinc-500">
            No changes between v{base?.id} and v{latest.id} — the specs and
            rendered files are identical.
          </p>
        </div>
      )}

      {!loading && !error && diff && !empty && (
        <div className="p-4">
          {diff.spec_changes.length > 0 && (
            <section aria-label="Spec changes">
              <h2 className="mb-2 text-xs font-medium uppercase tracking-wide text-zinc-500">
                Spec changes ({diff.spec_changes.length})
              </h2>
              <ul className="mb-6 overflow-hidden rounded-md border border-zinc-800">
                {diff.spec_changes.map((c, i) => {
                  const kind =
                    c.old_value === null
                      ? "added"
                      : c.new_value === null
                        ? "removed"
                        : "changed";
                  const color =
                    kind === "added"
                      ? "text-emerald-300"
                      : kind === "removed"
                        ? "text-red-300"
                        : "text-amber-300";
                  return (
                    <li
                      key={i}
                      className="border-b border-zinc-800/60 px-3 py-2 last:border-0"
                    >
                      <span className={`mr-2 text-[10px] font-medium uppercase ${color}`}>
                        {kind}
                      </span>
                      <code className="font-mono text-xs text-zinc-200">
                        {c.path}
                      </code>
                      <div className="mt-1 font-mono text-[11px] leading-relaxed">
                        {c.old_value !== null && (
                          <span className="text-red-400/80">
                            − {compact(c.old_value)}
                          </span>
                        )}
                        {c.new_value !== null && (
                          <span className="block text-emerald-400/80">
                            + {compact(c.new_value)}
                          </span>
                        )}
                      </div>
                    </li>
                  );
                })}
              </ul>
            </section>
          )}

          <section aria-label="File changes">
            <h2 className="mb-2 text-xs font-medium uppercase tracking-wide text-zinc-500">
              Files changed ({fileEntries.length})
            </h2>
            <div className="flex flex-col gap-4">
              {fileEntries.map(({ path, diff: d, added, removed }) => (
                <div
                  key={path}
                  className="overflow-hidden rounded-md border border-zinc-800"
                >
                  <div className="flex items-center gap-2 border-b border-zinc-800 bg-[#101013] px-3 py-2">
                    <FileDiff size={14} className="shrink-0 text-zinc-500" />
                    <code className="font-mono text-xs text-zinc-200">{path}</code>
                    <span className="ml-auto font-mono text-[11px]">
                      <span className="text-emerald-400">+{added}</span>{" "}
                      <span className="text-red-400">−{removed}</span>
                    </span>
                  </div>
                  <div className="overflow-x-auto py-2 font-mono text-[12px] leading-5">
                    {d.split("\n").map((line, i) => (
                      <DiffLine key={i} line={line} />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
