export const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, init);
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed with HTTP ${response.status}`);
  }
  return response.json() as Promise<T>;
}
