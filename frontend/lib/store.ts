import { create } from "zustand";

export type GenStatus = "idle" | "loading" | "error" | "done";

interface Spec2RunState {
  prompt: string;
  spec: Record<string, unknown> | null;
  status: GenStatus;
  error: string | null;
  questions: string[];
  answers: string[];
  auth: boolean;
  setPrompt: (p: string) => void;
  setSpec: (s: Record<string, unknown> | null) => void;
  setStatus: (s: GenStatus) => void;
  setError: (e: string | null) => void;
  setQuestions: (q: string[]) => void;
  setAnswers: (a: string[]) => void;
  setAuth: (a: boolean) => void;
}

export const useSpec2RunStore = create<Spec2RunState>((set) => ({
  prompt: "",
  spec: null,
  status: "idle",
  error: null,
  questions: [],
  answers: [],
  auth: false,
  setPrompt: (prompt) => set({ prompt }),
  setSpec: (spec) => set({ spec }),
  setStatus: (status) => set({ status }),
  setError: (error) => set({ error }),
  setQuestions: (questions) => set({ questions, answers: questions.map(() => "") }),
  setAnswers: (answers) => set({ answers }),
  setAuth: (auth) => set({ auth }),
}));
