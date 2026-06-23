export type ConnectionState = 'CONNECTED' | 'DISCONNECTED' | 'CONNECTING' | 'ERROR';

const DEFAULT_BACKEND_URL = 'http://127.0.0.1:8000';
const STORAGE_KEY = 'TAKSH_BACKEND_URL';

/**
 * Resolves the backend URL based on priority:
 * 1. Saved localStorage setting
 * 2. Environment variable VITE_TAKSH_BACKEND_URL
 * 3. Fallback http://127.0.0.1:8000
 */
export function getBackendUrl(): string {
  // 1. Saved localStorage setting
  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved) {
    return saved;
  }

  // 2. Environment variable
  const envUrl = (import.meta.env.VITE_TAKSH_BACKEND_URL as string) || '';
  if (envUrl) {
    return envUrl;
  }

  // 3. Fallback
  return DEFAULT_BACKEND_URL;
}

/**
 * Save user override for BACKEND_URL locally.
 */
export function saveBackendUrl(url: string): void {
  if (!url) {
    localStorage.removeItem(STORAGE_KEY);
  } else {
    // Normalize URL: remove trailing slash
    const normalized = url.replace(/\/$/, '');
    localStorage.setItem(STORAGE_KEY, normalized);
  }
}
