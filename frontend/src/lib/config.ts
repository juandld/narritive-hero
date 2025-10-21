// Centralized frontend configuration
// Prefer build-time env (VITE_BACKEND_URL). Otherwise, compute at runtime
// using the current page's host and port 8000 (backend default).
const env = (import.meta as any)?.env || {};

function computeRuntimeBackend(): string {
  try {
    if (typeof window !== 'undefined' && window.location) {
      const { protocol, hostname } = window.location;
      return `${protocol}//${hostname}:8000`;
    }
  } catch {}
  return 'http://localhost:8000';
}

export const BACKEND_URL: string = env.VITE_BACKEND_URL || computeRuntimeBackend();
