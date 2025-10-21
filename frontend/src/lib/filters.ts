import type { Note } from './types';
import type { Filters } from '$lib/stores/filters';

function isAudio(name: string): boolean { return /\.(wav|ogg|webm|m4a|mp3)$/i.test(name || ''); }

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

  const filtered = notes.filter((n) => {
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

  // Sorting
  const dir = filters.sortDir === 'asc' ? 1 : -1;
  const key = filters.sortKey || 'date';
  const getLenRaw = (n: Note): number | null => {
    if (typeof n.length_seconds === 'number' && Number.isFinite(n.length_seconds)) return n.length_seconds as number;
    const d = computedDurations[n.filename];
    return typeof d === 'number' && Number.isFinite(d) ? d : null;
  };
  const getLenForSort = (n: Note): number => {
    const v = getLenRaw(n);
    if (v == null) {
      // Place unknowns at end regardless of sort direction
      return filters.sortDir === 'asc' ? Number.POSITIVE_INFINITY : Number.NEGATIVE_INFINITY;
    }
    return v;
  };
  const getType = (n: Note): number => (isAudio(n.filename) ? 0 : 1);
  const getDate = (n: Note): number => {
    // Prefer explicit date
    if (n.date) {
      const d = new Date(n.date).getTime();
      if (Number.isFinite(d)) return d;
    }
    // Fallback: try to parse leading YYYYMMDD from filename
    const m = (n.filename || '').match(/^(\d{4})(\d{2})(\d{2})/);
    if (m) {
      const y = Number(m[1]); const mo = Number(m[2]) - 1; const da = Number(m[3]);
      const t = new Date(y, mo, da).getTime();
      if (Number.isFinite(t)) return t;
    }
    return 0;
  };
  const getLang = (n: Note): string => (n.language || 'und');

  const cmp = (a: Note, b: Note): number => {
    // Primary comparison by selected key
    let primary = 0;
    if (key === 'date') {
      primary = (getDate(a) < getDate(b) ? -1 : getDate(a) > getDate(b) ? 1 : 0);
    } else if (key === 'type') {
      primary = (getType(a) < getType(b) ? -1 : getType(a) > getType(b) ? 1 : 0);
    } else if (key === 'length') {
      primary = (getLenForSort(a) < getLenForSort(b) ? -1 : getLenForSort(a) > getLenForSort(b) ? 1 : 0);
    } else if (key === 'language') {
      primary = getLang(a).localeCompare(getLang(b));
    }
    if (primary !== 0) return dir * primary;
    // Tie-breakers for stable, visible movement
    // 1) Date (desc default) as universal fallback
    let tb = (getDate(a) < getDate(b) ? -1 : getDate(a) > getDate(b) ? 1 : 0);
    if (tb !== 0) return dir * (key === 'date' ? tb : tb);
    // 2) Filename as final tie-breaker (asc lexical)
    tb = (a.filename || '').localeCompare(b.filename || '');
    return tb;
  };
  const sorted = filtered.slice().sort(cmp);
  // no debug logs in production
  return sorted;
}
