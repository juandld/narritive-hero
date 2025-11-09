import { appActions } from '$lib/services/appActions';
import { notes as notesStore } from '$lib/stores/notes';
import { folders as foldersStore, selectedFolder as selectedFolderStore } from '$lib/stores/folders';
import { dbg } from '$lib/debug';
import { get } from 'svelte/store';

async function refreshAll() {
  const { notes, folders } = await appActions.fetchNotesAndFolders();
  notesStore.set(notes);
  foldersStore.set(folders);
}

function getSelectedFolder(): string | undefined {
  let v: string = '__ALL__';
  try { const unsub = selectedFolderStore.subscribe((x) => (v = x as any)); if (typeof unsub === 'function') (unsub as any)(); } catch {}
  if (v && v !== '__ALL__' && v !== '__UNFILED__') return v;
  return undefined;
}

export async function uploadBlob(blob: Blob, skipPoll = false) {
  const folder = getSelectedFolder();
  dbg('uploads:uploadBlob', { folder });
  const { filename } = await appActions.uploadNote(blob as any, folder);
  if (skipPoll) {
    await refreshAll();
    return;
  }
  const start = Date.now();
  const timeoutMs = 60_000; // 1 min cap
  const poll = async (delay = 2500): Promise<void> => {
    await refreshAll();
    const notes = (get(notesStore) || []) as any[];
    const note = notes.find((n) => n.filename === filename);
    if (note && note.transcription) {
      return;
    }
    if (Date.now() - start > timeoutMs) return;
    const nextDelay = Math.min(delay * 1.5, 8000);
    setTimeout(() => { poll(nextDelay); }, nextDelay);
  };
  await poll(2500);
}

export async function handleFiles(files: File[]) {
  for (const f of files) {
    await uploadBlob(f, true);
  }
  // open a short polling window
  const started = Date.now();
  const end = started + 30_000;
  const loop = async (delay = 2500) => {
    await refreshAll();
    if (Date.now() < end) {
      const nextDelay = Math.min(delay * 1.5, 8000);
      setTimeout(() => { loop(nextDelay); }, nextDelay);
    }
  };
  setTimeout(() => { loop(2500); }, 0);
}
