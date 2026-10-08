"use client";

import GenerationPanel from "@/components/GenerationPanel";
import PromptStudio from "@/components/PromptStudio";

export default function Home() {
  return (
    <main className="flex h-screen">
      <section className="w-[420px] shrink-0 border-r border-zinc-800">
        <PromptStudio />
      </section>
      <section className="min-w-0 flex-1">
        <GenerationPanel />
      </section>
    </main>
  );
}
