// Centralized frontend configuration
// Priority:
// 1) Build-time env (VITE_BACKEND_URL)
// 2) Runtime:
//    - If on localhost:5173 (dev), default to http://localhost:8000
//    - Otherwise, same-origin without explicit port (80/443 fallback)
function computeRuntimeBackend(): string {
  try {
    if (typeof window !== 'undefined' && window.location) {
      const { protocol, hostname, port } = window.location;
      // Any localhost dev port should target the backend dev server on :8000
      if (hostname === 'localhost' || hostname === '127.0.0.1') {
        return 'http://localhost:8000';
      }
      // Default to same-origin (implicit 80/443). Assumes a reverse proxy routes /api and /voice_notes.
      return `${protocol}//${hostname}`;
    }
  } catch {}
  // SSR or unknown environment: fall back to dev backend
  return 'http://localhost:8000';
}

import { env as publicEnv } from '$env/dynamic/public';

export const BACKEND_URL: string = publicEnv.PUBLIC_BACKEND_URL || computeRuntimeBackend();
