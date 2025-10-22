export function dbg(...args: any[]) {
  try {
    if (typeof window === 'undefined') return;
    const flag = (window as any).__NH_DEBUG === true || localStorage.getItem('nh_debug') === '1';
    if (!flag) return;
    // eslint-disable-next-line no-console
    console.log('[NH]', ...args);
  } catch {}
}

