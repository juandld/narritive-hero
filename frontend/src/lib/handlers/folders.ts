import { moveToFolder, createFolder, createFolderAndMove } from '$lib/services/pageActions';

export async function onMoveToFolder(e: CustomEvent<{ folder: string; filenames: string[] }>) {
  const { folder, filenames } = e.detail || { folder: '', filenames: [] };
  if (!folder || !filenames?.length) return;
  await moveToFolder(folder, filenames);
}

export async function onCreateFolder(e: CustomEvent<{ name: string }>) {
  const { name } = e.detail || { name: '' };
  if (!name) return;
  await createFolder(name);
}

export async function onCreateFolderAndMove(e: CustomEvent<{ name: string; filenames: string[] }>) {
  const { name, filenames } = e.detail || { name: '', filenames: [] };
  if (!name) return;
  await createFolderAndMove(name, filenames || []);
}

