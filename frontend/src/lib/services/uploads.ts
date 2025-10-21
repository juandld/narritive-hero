import { appActions } from '$lib/services/appActions';
import { notes as notesStore } from '$lib/stores/notes';
import { folders as foldersStore } from '$lib/stores/folders';

async function refreshAll() {
  const { notes, folders } = await appActions.fetchNotesAndFolders();
  notesStore.set(notes);
  foldersStore.set(folders);
}

export async function uploadBlob(blob: Blob, skipPoll = false) {
  const { filename } = await appActions.uploadNote(blob);
  if (skipPoll) {
    await refreshAll();
    return;
  }
  const start = Date.now();
  const timeoutMs = 60_000; // 1 min cap
  const poll = async (): Promise<void> => {
    await refreshAll();
    const notes = (await new Promise<any>((resolve) => notesStore.subscribe((v) => resolve(v))())) as any[];
    const note = notes.find((n) => n.filename === filename);
    if (note && note.transcription) {
      return;
    }
    if (Date.now() - start > timeoutMs) return;
    setTimeout(poll, 2000);
  };
  await poll();
}

export async function handleFiles(files: File[]) {
  for (const f of files) {
    await uploadBlob(f, true);
  }
  // open a short polling window
  const started = Date.now();
  const end = started + 30_000;
  const loop = async () => {
    await refreshAll();
    if (Date.now() < end) setTimeout(loop, 2000);
  };
  setTimeout(loop, 0);
}

