import { uiActions } from '$lib/stores/ui';

export function onToggleExpand(e: CustomEvent<string> | string) {
  const filename = typeof e === 'string' ? e : e?.detail;
  if (!filename || typeof filename !== 'string') return;
  uiActions.toggleExpand(filename);
}
