// Centralized frontend configuration
// Priority:
// 1) Build-time env (VITE_BACKEND_URL)
// 2) Heuristic at runtime: if current host starts with "front.", prefer matching
//    "back." subdomain; otherwise default to current host on port 8000.
const env = (import.meta as any)?.env || {};

function computeRuntimeBackend(): string {
  try {
    if (typeof window !== 'undefined' && window.location) {
      const { protocol, hostname } = window.location;
      // If using split front/back subdomains (e.g., front.example.com), prefer back.example.com
      const guessBack = hostname.startsWith('front.')
        ? `back.${hostname.slice('front.'.length)}`
        : hostname;
      // If we changed the hostname, assume default HTTPS port with no explicit :8000
      if (guessBack !== hostname) return `${protocol}//${guessBack}`;
      // Otherwise, default to backend on :8000 at same host
      return `${protocol}//${hostname}:8000`;
    }
  } catch {}
  return 'http://localhost:8000';
}

export const BACKEND_URL: string = env.VITE_BACKEND_URL || computeRuntimeBackend();
