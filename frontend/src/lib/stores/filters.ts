import { writable } from 'svelte/store';
export type SortKey = 'date' | 'type' | 'length' | 'language';
export type SortDir = 'asc' | 'desc';
export type Filters = { dateFrom: string; dateTo: string; topics: string; minLen: number | ''; maxLen: number | ''; search: string; sortKey: SortKey; sortDir: SortDir };
export const filters = writable<Filters>({ dateFrom: '', dateTo: '', topics: '', minLen: '', maxLen: '', search: '', sortKey: 'date', sortDir: 'desc' });
