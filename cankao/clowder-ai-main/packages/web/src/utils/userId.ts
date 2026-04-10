/**
 * Unified userId source for the frontend.
 * Priority: URL ?userId= > localStorage > 'default-user'
 */

const STORAGE_KEY = 'cat-cafe-userId';
const DEFAULT_USER = 'default-user';

export function getUserId(): string {
  if (typeof window === 'undefined') return DEFAULT_USER;

  const url = new URL(window.location.href);
  const fromUrl = url.searchParams.get('userId');
  if (fromUrl) {
    localStorage.setItem(STORAGE_KEY, fromUrl);
    return fromUrl;
  }

  return localStorage.getItem(STORAGE_KEY) ?? DEFAULT_USER;
}

export function setUserId(id: string): void {
  if (typeof window !== 'undefined') {
    localStorage.setItem(STORAGE_KEY, id);
  }
}
