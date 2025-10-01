import type { Note } from '$lib/types';
import { BACKEND_URL } from '$lib/config';

export async function ensureDurations(
  notes: Note[],
  computedDurations: Record<string, number>
): Promise<void> {
  const targets = notes.filter(
    (n) => n && n.filename && (n.length_seconds == null) && !(n.filename in computedDurations)
  );
  for (const n of targets) {
    const dur = await loadDurationFor(n.filename);
    if (dur != null) computedDurations[n.filename] = dur;
  }
}

function loadDurationFor(filename: string): Promise<number | null> {
  return new Promise((resolve) => {
    try {
      const audio = new Audio();
      audio.preload = 'metadata';
      audio.src = `${BACKEND_URL}/voice_notes/${filename}`;
      const cleanup = () => {
        audio.onloadedmetadata = null;
        audio.onerror = null;
      };
      audio.onloadedmetadata = () => {
        const dur = Number.isFinite(audio.duration) ? Math.round(audio.duration * 100) / 100 : NaN;
        cleanup();
        resolve(Number.isFinite(dur) ? dur : null);
      };
      audio.onerror = () => { cleanup(); resolve(null); };
    } catch (e) {
      resolve(null);
    }
  });
}

