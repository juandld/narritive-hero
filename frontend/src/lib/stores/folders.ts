import { writable } from 'svelte/store';
import type { FolderInfo } from '$lib/types';
import { api } from '$lib/api';

export const folders = writable<FolderInfo[]>([]);
export const selectedFolder = writable<string>('__ALL__');

export const folderActions = {
  async refresh() { folders.set(await api.getFolders()); },
  selectAll() { selectedFolder.set('__ALL__'); },
  selectUnfiled() { selectedFolder.set('__UNFILED__'); },
  select(name: string) { selectedFolder.set(name); },
};
