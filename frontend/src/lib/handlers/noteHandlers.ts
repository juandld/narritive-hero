import { uiActions } from '$lib/stores/ui';

export function onToggleExpand(e: CustomEvent<string> | any) {
  const filename = (e?.detail && typeof e.detail === 'string') ? e.detail : e;
  if (!filename) return;
  uiActions.toggleExpand(filename);
}

