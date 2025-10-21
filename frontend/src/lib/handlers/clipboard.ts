export async function onCopy(e?: CustomEvent<string>) {
  try {
    const text = e?.detail || '';
    if (!text) return;
    await navigator.clipboard.writeText(text);
  } catch {}
}
