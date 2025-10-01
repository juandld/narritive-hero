import { writable } from 'svelte/store';
export type Filters = { dateFrom: string; dateTo: string; topics: string; minLen: number | ''; maxLen: number | ''; search: string };
export const filters = writable<Filters>({ dateFrom: '', dateTo: '', topics: '', minLen: '', maxLen: '', search: '' });
