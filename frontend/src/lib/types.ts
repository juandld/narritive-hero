export type Tag = { label: string; color?: string };
export type Note = {
  filename: string;
  transcription?: string;
  title?: string;
  date?: string; // YYYY-MM-DD
  created_at?: string; // ISO timestamp
  created_ts?: number; // epoch ms
  length_seconds?: number;
  topics?: string[];
  language?: string;
  folder?: string;
  tags?: Tag[];
};

export type FolderInfo = { name: string; count: number };
export type Format = { id: string; title: string; prompt: string };
