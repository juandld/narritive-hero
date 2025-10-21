import { BACKEND_URL } from '$lib/config';

export type GenerateOptions = {
  extra_text?: string;
  provider?: string;
  model?: string;
  temperature?: number;
  format_ids?: string[];
};

export async function generateNarrative(
  items: { filename: string }[],
  opts: GenerateOptions
): Promise<{ filename: string | null }> {
  const res = await fetch(`${BACKEND_URL}/api/narratives/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      items,
      extra_text: opts.extra_text,
      provider: opts.provider,
      model: opts.model || undefined,
      temperature: opts.temperature,
      format_ids: opts.format_ids,
    }),
  });
  if (!res.ok) throw new Error('Failed to generate narrative');
  const data = await res.json();
  const fname = (data && data.filename) || null;
  return { filename: fname };
}

