const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface GenerateOptions {
  auth: boolean;
  database: "postgres";
  language: "python";
}

async function postJson(path: string, body: unknown): Promise<Record<string, unknown>> {
  const r = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    const detail = await r.json().catch(() => ({}));
    const msg =
      typeof detail.detail === "string" ? detail.detail : `request failed: ${r.status}`;
    throw new Error(msg);
  }
  return r.json();
}

export function generateSpec(
  prompt: string,
  options: GenerateOptions,
): Promise<Record<string, unknown>> {
  return postJson("/specs/generate", {
    prompt,
    auth: options.auth,
    database: options.database,
    language: options.language,
  });
}

export function refineSpec(
  prompt: string,
  questions: string[],
  answers: string[],
  auth: boolean,
): Promise<Record<string, unknown>> {
  return postJson("/specs/refine", { prompt, questions, answers, auth });
}

export function importSpec(payload: {
  url?: string;
  content?: string;
}): Promise<Record<string, unknown>> {
  return postJson("/specs/import", payload);
}

export async function generateCode(
  spec: Record<string, unknown>,
): Promise<Record<string, string>> {
  const r = await fetch(`${API_URL}/generate/code`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ spec }),
  });
  if (!r.ok) throw new Error(`code generation failed: ${r.status}`);
  return r.json();
}
