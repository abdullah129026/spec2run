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
): Promise<{ files: Record<string, string> }> {
  const r = await fetch(`${API_URL}/generate/code`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ spec }),
  });
  if (!r.ok) throw new Error(`code generation failed: ${r.status}`);
  return r.json();
}

export interface SpecChange {
  path: string;
  old_value: unknown;
  new_value: unknown;
}

export interface DiffResult {
  spec_changes: SpecChange[];
  file_diffs: Record<string, string>;
}

export function patchSpec(
  spec: Record<string, unknown>,
  prompt: string,
  auth: boolean,
): Promise<Record<string, unknown>> {
  return postJson("/specs/patch", { spec, prompt, auth });
}

export async function diffVersions(
  oldSpec: Record<string, unknown>,
  newSpec: Record<string, unknown>,
): Promise<DiffResult> {
  const r = await postJson("/generate/diff", {
    old_spec: oldSpec,
    new_spec: newSpec,
  });
  return r as unknown as DiffResult;
}

export async function downloadZip(
  spec: Record<string, unknown>,
  auth: boolean,
): Promise<void> {
  const r = await fetch(`${API_URL}/generate/zip`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ spec, auth }),
  });
  if (!r.ok) {
    const detail = await r.json().catch(() => ({}));
    throw new Error(
      typeof detail.detail === "string"
        ? detail.detail
        : `zip download failed: ${r.status}`,
    );
  }
  const blob = await r.blob();
  const name =
    r.headers
      .get("Content-Disposition")
      ?.match(/filename="([^"]+)"/)?.[1] ?? "spec2run-service.zip";
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export interface GithubPushResult {
  repo: string;
  url: string;
}

export function pushToGithub(
  spec: Record<string, unknown>,
  token: string,
  repo: string,
  description: string,
  isPrivate: boolean,
  auth: boolean,
): Promise<GithubPushResult> {
  return postJson("/generate/github", {
    spec,
    token,
    repo,
    description,
    private: isPrivate,
    auth,
  }) as unknown as Promise<GithubPushResult>;
}
