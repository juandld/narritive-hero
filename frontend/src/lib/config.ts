// Centralized frontend configuration
// Uses Vite env at build time; falls back to localhost for dev.
// Set VITE_BACKEND_URL in your environment or docker build args.
const env = (import.meta as any)?.env || {};
export const BACKEND_URL: string = env.VITE_BACKEND_URL || 'http://localhost:8000';
