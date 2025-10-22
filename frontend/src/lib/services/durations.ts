import type { Note } from '$lib/types';
import { BACKEND_URL } from '$lib/config';
import { dbg } from '$lib/debug';

function isAudioFilename(name: string): boolean {
  return /\.(wav|ogg|webm|m4a|mp3)$/i.test(name || '');
}

export async function ensureDurations(
  notes: Note[],
  computedDurations: Record<string, number>
): Promise<void> {
  const targets = notes.filter((n) =>
    n && n.filename && isAudioFilename(n.filename) && (n.length_seconds == null) && !(n.filename in computedDurations)
  );
  dbg('durations:targets', targets.map((n) => n.filename));
  for (const n of targets) {
    const dur = await loadDurationFor(n.filename);
    if (dur != null) computedDurations[n.filename] = dur;
    dbg('durations:loaded', n.filename, dur);
  }
}

function loadDurationFor(filename: string): Promise<number | null> {
  return new Promise((resolve) => {
    try {
      const audio = new Audio();
      audio.preload = 'metadata';
      audio.src = `${BACKEND_URL}/voice_notes/${encodeURIComponent(filename)}`;
      dbg('durations:loading', audio.src);
      const cleanup = () => {
        audio.onloadedmetadata = null;
        audio.onerror = null;
      };
      audio.onloadedmetadata = () => {
        const dur = Number.isFinite(audio.duration) ? Math.round(audio.duration * 100) / 100 : NaN;
        cleanup();
        resolve(Number.isFinite(dur) ? dur : null);
      };
      audio.onerror = (e) => { cleanup(); dbg('durations:error', filename); resolve(null); };
    } catch (e) {
      dbg('durations:exception', filename, e);
      resolve(null);
    }
  });
}
