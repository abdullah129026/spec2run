const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function generateSpec(
  prompt: string,
  options: Record<string, unknown>,
): Promise<Record<string, unknown>> {
  const r = await fetch(`${API_URL}/specs/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt, options }),
  });
  if (!r.ok) throw new Error(`spec generation failed: ${r.status}`);
  return r.json();
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
