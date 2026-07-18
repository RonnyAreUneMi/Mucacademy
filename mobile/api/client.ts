/**
 * Cliente API minimalista para el backend Django/DRF.
 *
 * Resuelve la URL base SIN depender de una IP fija: usa la IP del servidor de
 * desarrollo de Expo (la misma con la que el teléfono cargó la app) y le pega
 * el puerto del backend. Así funciona en CUALQUIER red sin editar app.json.
 * Si no hay dev-server (build nativo), cae a `extra.apiBaseUrl` y por último a
 * localhost. Agrega automáticamente el header `Authorization: Token <key>`.
 *
 * Uso:
 *   import { api } from '@/api/client';
 *   const me = await api.get<Participant>('/api/v1/public/account/me/');
 *   const res = await api.post('/api/v1/public/account/login/', { email, password });
 */
import Constants from 'expo-constants';
import * as SecureStore from 'expo-secure-store';

const TOKEN_KEY = 'certifai.token';

const CONFIGURED_URL = (Constants.expoConfig?.extra as any)?.apiBaseUrl as
  | string
  | undefined;

/**
 * Deriva la URL del backend a partir del host del servidor de Expo (Metro),
 * que es la IP LAN de la máquina de desarrollo. Funciona en cualquier WiFi.
 */
function resolveBaseUrl(): string {
  // Puerto del backend: del apiBaseUrl configurado, o 8500 por defecto.
  const portMatch = CONFIGURED_URL?.match(/:(\d+)(?:\/|$)/);
  const port = portMatch ? portMatch[1] : '8500';

  // IP del host de desarrollo (ej. '192.168.0.107:8081').
  const hostUri =
    Constants.expoConfig?.hostUri ??
    (Constants as any).expoGoConfig?.debuggerHost ??
    (Constants as any).manifest2?.extra?.expoGo?.debuggerHost ??
    (Constants as any).manifest?.debuggerHost;

  const host = hostUri ? String(hostUri).split(':')[0] : '';
  if (host && host !== 'localhost' && host !== '127.0.0.1') {
    return `http://${host}:${port}`;
  }
  return CONFIGURED_URL ?? 'http://localhost:8500';
}

const BASE_URL = resolveBaseUrl();

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
