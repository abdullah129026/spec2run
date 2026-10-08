"use client";

import { useState } from "react";
import { Mic } from "lucide-react";

const EXAMPLES = [
  "Create an API for a bookstore with books, authors, and orders. Books have title and price. I need JWT auth.",
  "A todo API with lists and items. Items have a title and a done flag.",
  "A blog API with posts and comments. Posts have title, body, and tags.",
];

export default function PromptStudio() {
  const [prompt, setPrompt] = useState("");

  return (
    <div className="flex h-full flex-col gap-4 overflow-y-auto p-5">
      <div>
        <h1 className="text-lg font-semibold">Spec2Run</h1>
        <p className="mt-1 text-sm text-zinc-400">
          Describe the API you want, or press the mic and say it.
        </p>
      </div>

      <button
        type="button"
        className="flex items-center justify-center gap-2 rounded-md bg-indigo-600 px-4 py-2.5 text-sm font-medium hover:bg-indigo-500"
      >
        <Mic size={16} />
        Press and speak your API
      </button>

      <textarea
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        placeholder="Create an API for a bookstore..."
        rows={6}
        className="rounded-md border border-zinc-800 bg-zinc-900 p-3 text-sm outline-none placeholder:text-zinc-600 focus:border-indigo-600"
      />

      <div className="flex flex-wrap gap-2">
        {["Auth required?", "Postgres", "Python"].map((label) => (
          <button
            key={label}
            type="button"
            className="rounded-full border border-zinc-700 px-3 py-1 text-xs text-zinc-400 hover:border-zinc-500 hover:text-zinc-200"
          >
            {label}
          </button>
        ))}
      </div>

      <button
        type="button"
        disabled={!prompt.trim()}
        className="rounded-md bg-zinc-100 px-4 py-2 text-sm font-medium text-zinc-950 hover:bg-white disabled:cursor-not-allowed disabled:opacity-40"
      >
        Generate API
      </button>

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
    </div>
  );
}
