"use client";

import { useState } from "react";

const TABS = ["Swagger", "Code", "Logs"] as const;
type Tab = (typeof TABS)[number];

export default function GenerationPanel() {
  const [tab, setTab] = useState<Tab>("Swagger");

  return (
    <div className="flex h-full flex-col">
      <div className="flex gap-1 border-b border-zinc-800 px-4">
        {TABS.map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
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
      <div className="flex flex-1 items-center justify-center p-8 text-center">
        <p className="max-w-sm text-sm leading-relaxed text-zinc-600">
          Generate a spec from the left panel and the live {tab.toLowerCase()}{" "}
          view will appear here.
        </p>
      </div>
    </div>
  );
}
