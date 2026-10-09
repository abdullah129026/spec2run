"use client";

import { useState } from "react";
import { useSpec2RunStore } from "@/lib/store";
import SwaggerTab from "./SwaggerTab";

const TABS = ["Swagger", "Code", "Logs"] as const;
type Tab = (typeof TABS)[number];

const TAB_EXAMPLES: Record<Tab, string> = {
  Swagger: "Create an API for a bookstore with books, authors, and orders.",
  Code: "A todo API with lists and items. Items have a title and a done flag.",
  Logs: "A blog API with posts and comments. Posts have title, body, and tags.",
};

const TAB_NOTES: Record<Tab, string> = {
  Swagger: "The live API reference will appear here.",
  Code: "Editable generated code lands in the week-2 slice.",
  Logs: "Staged build logs stream in with the week-3 sandbox.",
};

export default function GenerationPanel() {
  const [tab, setTab] = useState<Tab>("Swagger");
  const spec = useSpec2RunStore((s) => s.spec);
  const status = useSpec2RunStore((s) => s.status);
  const error = useSpec2RunStore((s) => s.error);
  const setPrompt = useSpec2RunStore((s) => s.setPrompt);

  return (
    <div className="flex h-full flex-col">
      <div className="flex gap-1 border-b border-zinc-800 px-4">
        {TABS.map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            aria-selected={tab === t}
            role="tab"
            className={`px-4 py-3 text-sm ${
              tab === t
                ? "border-b-2 border-indigo-500 text-zinc-100"
                : "text-zinc-500 hover:text-zinc-300"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === "Swagger" && status === "loading" && (
        <div aria-hidden className="flex flex-col gap-3 p-6">
          <div className="h-8 w-1/3 animate-pulse rounded bg-zinc-800" />
          <div className="h-12 animate-pulse rounded bg-zinc-800" />
          <div className="h-12 animate-pulse rounded bg-zinc-800" />
          <div className="h-12 w-2/3 animate-pulse rounded bg-zinc-800" />
        </div>
      )}

      {tab === "Swagger" && status === "error" && error && (
        <div className="flex flex-1 items-center justify-center p-8">
          <div className="max-w-sm rounded-md border border-red-900/60 bg-red-950/30 p-4 text-center">
            <p className="text-sm font-medium text-red-300">Generation failed</p>
            <p className="mt-1 text-xs leading-relaxed text-red-400">{error}</p>
          </div>
        </div>
      )}

      {tab === "Swagger" && spec && status === "done" && (
        <div className="min-h-0 flex-1">
          <SwaggerTab />
        </div>
      )}

      {(tab !== "Swagger" || (!spec && status === "idle")) && (
        <div className="flex flex-1 items-center justify-center p-8">
          <div className="max-w-sm text-center">
            <p className="text-sm leading-relaxed text-zinc-500">
              {TAB_NOTES[tab]}
            </p>
            <button
              type="button"
              onClick={() => setPrompt(TAB_EXAMPLES[tab])}
              className="mt-4 rounded-md border border-zinc-800 p-3 text-left text-xs leading-relaxed text-zinc-400 hover:border-zinc-600 hover:text-zinc-200"
            >
              {TAB_EXAMPLES[tab]}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
