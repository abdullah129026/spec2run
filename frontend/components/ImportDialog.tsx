"use client";

import { useEffect, useRef, useState } from "react";
import { FileUp, X } from "lucide-react";
import { importSpec } from "@/lib/api";
import { useSpec2RunStore } from "@/lib/store";

export default function ImportDialog({ onClose }: { onClose: () => void }) {
  const [mode, setMode] = useState<"url" | "paste">("url");
  const [value, setValue] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const setSpec = useSpec2RunStore((s) => s.setSpec);
  const setStatus = useSpec2RunStore((s) => s.setStatus);
  const inputRef = useRef<HTMLInputElement>(null);
  const textRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  useEffect(() => {
    (mode === "url" ? inputRef : textRef).current?.focus();
  }, [mode]);

  async function submit() {
    const trimmed = value.trim();
    if (!trimmed || busy) return;
    setBusy(true);
    setError(null);
    try {
      const spec = await importSpec(
        mode === "url" ? { url: trimmed } : { content: trimmed },
      );
      setSpec(spec);
      setStatus("done");
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "import failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      onClick={onClose}
      role="presentation"
    >
      <div
        className="w-full max-w-lg rounded-lg border border-zinc-800 bg-[#101013] p-5"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-label="Import OpenAPI document"
      >
        <div className="mb-4 flex items-center justify-between">
          <h2 className="flex items-center gap-2 text-sm font-semibold">
            <FileUp size={16} className="text-zinc-400" />
            Import an OpenAPI document
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close import dialog"
            className="rounded p-1 text-zinc-500 hover:text-zinc-200"
          >
            <X size={16} />
          </button>
        </div>

        <div className="mb-3 flex gap-1 rounded-md bg-zinc-900 p-1 text-xs">
          {(["url", "paste"] as const).map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => setMode(m)}
              className={`flex-1 rounded px-3 py-1.5 ${
                mode === m
                  ? "bg-zinc-800 text-zinc-100"
                  : "text-zinc-500 hover:text-zinc-300"
              }`}
            >
              {m === "url" ? "From URL" : "Paste JSON/YAML"}
            </button>
          ))}
        </div>

        {mode === "url" ? (
          <input
            ref={inputRef}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") submit();
            }}
            placeholder="https://petstore.swagger.io/v2/swagger.json"
            spellCheck={false}
            className="w-full rounded-md border border-zinc-800 bg-zinc-900 p-2.5 font-mono text-xs outline-none placeholder:text-zinc-600 focus:border-indigo-600"
          />
        ) : (
          <textarea
            ref={textRef}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder='{"openapi": "3.0.0", ...}'
            rows={8}
            spellCheck={false}
            className="w-full rounded-md border border-zinc-800 bg-zinc-900 p-2.5 font-mono text-xs outline-none placeholder:text-zinc-600 focus:border-indigo-600"
          />
        )}

        {error && (
          <p className="mt-3 rounded-md border border-red-900/60 bg-red-950/30 p-2.5 text-xs leading-relaxed text-red-400">
            {error}
          </p>
        )}

        <div className="mt-4 flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="rounded-md px-3 py-2 text-xs text-zinc-400 hover:text-zinc-200"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={submit}
            disabled={!value.trim() || busy}
            className="rounded-md bg-indigo-600 px-4 py-2 text-xs font-medium hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {busy ? "Importing…" : "Import spec"}
          </button>
        </div>
      </div>
    </div>
  );
}
