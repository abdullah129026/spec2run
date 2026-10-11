import { create } from "zustand";

export type GenStatus = "idle" | "loading" | "error" | "done";

export interface SpecVersion {
  id: number; // 1-based, like a release number
  label: string; // the prompt that produced it, truncated
  spec: Record<string, unknown>;
  files: Record<string, string> | null; // generated files, fetched lazily
  edits: Record<string, string>; // Monaco overrides, merged over files
  createdAt: number;
}

interface Spec2RunState {
  prompt: string;
  spec: Record<string, unknown> | null;
  status: GenStatus;
  error: string | null;
  questions: string[];
  answers: string[];
  auth: boolean;
  versions: SpecVersion[];
  currentVersion: number; // index into versions
  setPrompt: (p: string) => void;
  setStatus: (s: GenStatus) => void;
  setError: (e: string | null) => void;
  setQuestions: (q: string[]) => void;
  setAnswers: (a: string[]) => void;
  setAuth: (a: boolean) => void;
  addVersion: (label: string, spec: Record<string, unknown>) => void;
  setVersionFiles: (id: number, files: Record<string, string>) => void;
  setEditedFile: (id: number, path: string, content: string) => void;
  resetEdits: (id: number) => void;
  setCurrentVersion: (i: number) => void;
  resetAll: () => void;
}

export const useSpec2RunStore = create<Spec2RunState>((set) => ({
  prompt: "",
  spec: null,
  status: "idle",
  error: null,
  questions: [],
  answers: [],
  auth: false,
  versions: [],
  currentVersion: 0,
  setPrompt: (prompt) => set({ prompt }),
  setStatus: (status) => set({ status }),
  setError: (error) => set({ error }),
  setQuestions: (questions) => set({ questions, answers: questions.map(() => "") }),
  setAnswers: (answers) => set({ answers }),
  setAuth: (auth) => set({ auth }),
  addVersion: (label, spec) =>
    set((s) => {
      const version: SpecVersion = {
        id: s.versions.length + 1,
        label: label.length > 60 ? label.slice(0, 60) + "…" : label,
        spec,
        files: null,
        edits: {},
        createdAt: Date.now(),
      };
      return {
        versions: [...s.versions, version],
        currentVersion: s.versions.length,
        spec,
      };
    }),
  setVersionFiles: (id, files) =>
    set((s) => ({
      versions: s.versions.map((v) => (v.id === id ? { ...v, files } : v)),
    })),
  setEditedFile: (id, path, content) =>
    set((s) => ({
      versions: s.versions.map((v) =>
        v.id === id ? { ...v, edits: { ...v.edits, [path]: content } } : v,
      ),
    })),
  resetEdits: (id) =>
    set((s) => ({
      versions: s.versions.map((v) => (v.id === id ? { ...v, edits: {} } : v)),
    })),
  setCurrentVersion: (i) =>
    set((s) => ({
      currentVersion: i,
      // Deliberately does NOT touch `spec`: browsing history in the Diff tab
      // must not move the workspace away from the latest version.
    })),
  resetAll: () =>
    set({
      prompt: "",
      spec: null,
      status: "idle",
      error: null,
      questions: [],
      answers: [],
      versions: [],
      currentVersion: 0,
    }),
}));

/** Files actually in the editor: Monaco edits override generated files. */
export function effectiveFiles(v: SpecVersion): Record<string, string> | null {
  if (!v.files) return null;
  return { ...v.files, ...v.edits };
}
