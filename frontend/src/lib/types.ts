export type Tag = { label: string; color?: string };
export type Note = {
  filename: string;
  transcription?: string;
  title?: string;
  date?: string; // YYYY-MM-DD
  length_seconds?: number;
  topics?: string[];
  folder?: string;
  tags?: Tag[];
};

export type FolderInfo = { name: string; count: number };
export type Format = { id: string; title: string; prompt: string };

