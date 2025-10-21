import type { Note, FolderInfo } from '$lib/types';
import { api } from '$lib/api';

export const appActions = {
  async fetchNotesAndFolders(): Promise<{ notes: Note[]; folders: FolderInfo[] }> {
    const [notes, folders] = await Promise.all([api.getNotes(), api.getFolders()]);
    return { notes, folders };
  },

  // Notes
  async uploadNote(fileOrBlob: File | Blob): Promise<{ filename: string }> {
    return api.uploadNote(fileOrBlob);
  },
  async deleteNote(filename: string): Promise<void> {
    return api.deleteNote(filename);
  },
  async deleteNotes(filenames: string[]): Promise<void> {
    await Promise.all(filenames.map((f) => api.deleteNote(f)));
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

