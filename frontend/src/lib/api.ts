import { BACKEND_URL } from './config';
import type { Note, FolderInfo } from './types';

async function j<T>(res: Response): Promise<T> {
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return (await res.json()) as T;
}

export const api = {
  // Notes
  async getNotes(): Promise<Note[]> {
    const res = await fetch(`${BACKEND_URL}/api/notes`);
    return j<Note[]>(res);
  },
  async deleteNote(filename: string): Promise<void> {
    const res = await fetch(`${BACKEND_URL}/api/notes/${encodeURIComponent(filename)}`, { method: 'DELETE' });
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  },
  async uploadNote(fileOrBlob: File | Blob): Promise<{ filename: string }> {
    const formData = new FormData();
    formData.append('file', fileOrBlob, (fileOrBlob as File).name || 'recording.wav');
    const res = await fetch(`${BACKEND_URL}/api/notes`, { method: 'POST', body: formData });
    return j<{ filename: string }>(res);
  },
  async createTextNote(payload: { title?: string; transcription: string; date?: string; folder?: string; tags?: { label: string; color?: string }[] }): Promise<{ filename: string }>{
    const res = await fetch(`${BACKEND_URL}/api/notes/text`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return j<{ filename: string }>(res);
  },
  async patchNoteFolder(filename: string, folder: string): Promise<void> {
    const res = await fetch(`${BACKEND_URL}/api/notes/${encodeURIComponent(filename)}/folder`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ folder }),
    });
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  },

  // Folders
  async getFolders(): Promise<FolderInfo[]> {
    const res = await fetch(`${BACKEND_URL}/api/folders`);
    return j<FolderInfo[]>(res);
  },
  async createFolder(name: string): Promise<void> {
    const res = await fetch(`${BACKEND_URL}/api/folders`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name }),
    });
    if (!res.ok) throw new Error('create folder failed');
  },
  async deleteFolder(name: string): Promise<void> {
    const res = await fetch(`${BACKEND_URL}/api/folders/${encodeURIComponent(name)}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('delete folder failed');
  },
};
