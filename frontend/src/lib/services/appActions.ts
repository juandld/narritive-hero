import type { Note, FolderInfo } from '$lib/types';
import { api } from '$lib/api';

export const appActions = {
  async fetchNotesAndFolders(): Promise<{ notes: Note[]; folders: FolderInfo[] }> {
    const [notes, folders] = await Promise.all([api.getNotes(), api.getFolders()]);
    return { notes, folders };
  },

  // Notes
  async uploadNote(fileOrBlob: File | Blob, folder?: string): Promise<{ filename: string }> {
    return api.uploadNote(fileOrBlob, folder);
  },
  async deleteNote(filename: string): Promise<void> {
    return api.deleteNote(filename);
  },
  async deleteNotes(filenames: string[]): Promise<void> {
    const results = await Promise.allSettled(filenames.map((f) => api.deleteNote(f)));
    const failures = results
      .map((r, i) => ({ r, name: filenames[i] }))
      .filter((x) => x.r.status === 'rejected') as { r: PromiseRejectedResult; name: string }[];
    if (failures.length) {
      console.error(`Failed to delete ${failures.length} of ${filenames.length} notes`, failures.map(f => ({ filename: f.name, reason: String(f.r.reason) })));
      // Optional: throw to allow caller to surface a UI error
      // throw new Error(`Failed to delete: ${failures.map(f=>f.name).join(', ')}`);
    }
  },
  async moveNotesToFolder(filenames: string[], folder: string): Promise<void> {
    await Promise.all(filenames.map((f) => api.patchNoteFolder(f, folder)));
  },

  // Folders
  async createFolder(name: string): Promise<void> {
    return api.createFolder(name);
  },
  async deleteFolder(name: string): Promise<void> {
    return api.deleteFolder(name);
  },
};
