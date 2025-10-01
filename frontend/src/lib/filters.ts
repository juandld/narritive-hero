import type { Note } from './types';
import type { Filters } from '$lib/stores/filters';

export function applyFilters(
  notes: Note[],
  filters: Filters,
  selectedFolder: string,
  computedDurations: Record<string, number>
): Note[] {
  const from = filters.dateFrom ? new Date(filters.dateFrom) : null;
  const to = filters.dateTo ? new Date(filters.dateTo) : null;
  const topicTokens = (filters.topics || '')
    .toLowerCase()
    .split(/[ ,]+/)
    .map((t) => t.trim())
    .filter(Boolean);
  const minLen = typeof filters.minLen === 'number' && Number.isFinite(filters.minLen) ? (filters.minLen as number) : null;
  const maxLen = typeof filters.maxLen === 'number' && Number.isFinite(filters.maxLen) ? (filters.maxLen as number) : null;
  const q = (filters.search || '').trim().toLowerCase();

  return notes.filter((n) => {
    // Folder filter
    if (selectedFolder === '__UNFILED__') {
      if ((n as any).folder && (n as any).folder.trim() !== '') return false;
    } else if (selectedFolder && selectedFolder !== '__ALL__') {
      if ((n as any).folder !== selectedFolder) return false;
    }

    let len: number | null = null;
    if (typeof n.length_seconds === 'number' && Number.isFinite(n.length_seconds)) {
      len = n.length_seconds;
    } else if (typeof (n as any).length_seconds === 'string') {
      const parsed = Number((n as any).length_seconds);
      if (Number.isFinite(parsed)) len = parsed;
    }
    if (len == null && computedDurations[n.filename] != null) {
      len = computedDurations[n.filename];
    }
    // Date filter
    if (from || to) {
      if (!n.date) return false;
      const d = new Date(n.date);
      if (from && d < from) return false;
      if (to) {
        const end = new Date(to);
        end.setHours(23, 59, 59, 999);
        if (d > end) return false;
      }
    }
    // Topics filter (any match)
    if (topicTokens.length) {
      const noteTopics = (n.topics || []).map((t) => t.toLowerCase());
      const hasAny = topicTokens.some((t) => noteTopics.includes(t));
      if (!hasAny) return false;
    }
    // Length filter
    const passLen = !((minLen !== null && len !== null && len < minLen) || (maxLen !== null && len !== null && len > maxLen));
    if (!passLen) return false;
    // Text search across title + transcription
    if (q) {
      const hay = `${n.title ?? ''} ${n.transcription ?? ''}`.toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });
}
