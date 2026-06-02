/**
 * Cliente API minimalista para el backend Django/DRF.
 *
 * Lee la base URL desde app.json (`extra.apiBaseUrl`) y agrega automáticamente
 * el header `Authorization: Token <key>` si hay sesión activa.
 *
 * Uso:
 *   import { api } from '@/api/client';
 *   const me = await api.get<Participant>('/api/v1/public/account/me/');
 *   const res = await api.post('/api/v1/public/account/login/', { email, password });
 */
import Constants from 'expo-constants';
import * as SecureStore from 'expo-secure-store';

const TOKEN_KEY = 'certifai.token';

const BASE_URL =
  (Constants.expoConfig?.extra as any)?.apiBaseUrl ?? 'http://localhost:8500';

/**
 * URL pública HTTPS del backend, usada solo para flujos OAuth (Google) porque
 * Google bloquea IPs privadas como redirect_uri. Se setea en `app.json` →
 * `extra.webBaseUrl`. Si no está configurada, hace fallback a `BASE_URL`.
 */
export const WEB_BASE_URL =
  (Constants.expoConfig?.extra as any)?.webBaseUrl ?? BASE_URL;

export class APIError extends Error {
  status: number;
  data: any;
  constructor(status: number, data: any, message?: string) {
    super(message ?? data?.error ?? data?.detail ?? `HTTP ${status}`);
    this.status = status;
    this.data = data;
  }
}

async function getToken(): Promise<string | null> {
  try {
    return await SecureStore.getItemAsync(TOKEN_KEY);
  } catch {
    return null;
  }
}

export async function setToken(token: string | null) {
  if (token) {
    await SecureStore.setItemAsync(TOKEN_KEY, token);
  } else {
    await SecureStore.deleteItemAsync(TOKEN_KEY);
  }
}

async function request<T = any>(
  method: 'GET' | 'POST' | 'PATCH' | 'DELETE',
  path: string,
  body?: any,
): Promise<T> {
  const token = await getToken();
  const headers: Record<string, string> = {
    Accept: 'application/json',
  };
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (token) headers['Authorization'] = `Token ${token}`;

  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  let data: any = null;
  const text = await res.text();
  if (text) {
    try { data = JSON.parse(text); } catch { data = text; }
  }
  if (!res.ok) {
    throw new APIError(res.status, data);
  }
  return data as T;
}

export const api = {
  get:    <T = any>(path: string)            => request<T>('GET', path),
  post:   <T = any>(path: string, body?: any) => request<T>('POST', path, body),
  patch:  <T = any>(path: string, body?: any) => request<T>('PATCH', path, body),
  delete: <T = any>(path: string)             => request<T>('DELETE', path),
  baseUrl: BASE_URL,
  webBaseUrl: WEB_BASE_URL,
};
