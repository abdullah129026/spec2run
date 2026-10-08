import { create } from "zustand";

interface Spec2RunState {
  prompt: string;
  spec: Record<string, unknown> | null;
  setPrompt: (p: string) => void;
  setSpec: (s: Record<string, unknown> | null) => void;
}

export const useSpec2RunStore = create<Spec2RunState>((set) => ({
  prompt: "",
  spec: null,
  setPrompt: (prompt) => set({ prompt }),
  setSpec: (spec) => set({ spec }),
}));
