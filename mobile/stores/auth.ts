/**
 * Auth store · Zustand. Maneja sesión + token + participante actual.
 */
import { create } from 'zustand';

import { api, setToken } from '@/api/client';

export type Participant = {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
  national_id: string;
  phone: string;
  is_leader: boolean;
  nombre_completo: string;
  initials: string;
  avatar_url: string | null;
  last_login: string | null;
  created_at?: string;
};

type LoginResponse = {
  token: string;
  expires_at: string;
  participante: Participant;
};

type AuthState = {
  participante: Participant | null;
  loading: boolean;
  error: string | null;
  /** True una vez que terminó el primer refresh (haya o no sesión). */
  ready: boolean;

  login:    (email: string, password: string) => Promise<void>;
  register: (data: {
    nombres: string;
    apellidos: string;
    email: string;
    cedula?: string;
    celular?: string;
    password: string;
  }) => Promise<void>;
  /** Setea sesión a partir de un token recibido externamente (Google deep-link). */
  hydrateFromToken: (token: string) => Promise<void>;
  logout:   () => Promise<void>;
  refresh:  () => Promise<void>;
  clearError: () => void;
};

export const useAuth = create<AuthState>((set) => ({
  participante: null,
  loading: false,
  error: null,
  ready: false,

  login: async (email, password) => {
    set({ loading: true, error: null });
    try {
      const res = await api.post<LoginResponse>('/api/v1/public/account/login/', { email, password });
      await setToken(res.token);
      set({ participante: res.participante, loading: false });
    } catch (err: any) {
      set({ loading: false, error: err.message ?? 'Error al iniciar sesión' });
      throw err;
    }
  },

  register: async (data) => {
    set({ loading: true, error: null });
    try {
      const res = await api.post<LoginResponse>('/api/v1/public/account/register/', data);
      await setToken(res.token);
      set({ participante: res.participante, loading: false });
    } catch (err: any) {
      set({ loading: false, error: err.message ?? 'Error al crear cuenta' });
      throw err;
    }
  },

  hydrateFromToken: async (token) => {
    set({ loading: true, error: null });
    await setToken(token);
    try {
      const me = await api.get<Participant>('/api/v1/public/account/me/');
      set({ participante: me, loading: false });
    } catch (err: any) {
      await setToken(null);
      set({ loading: false, error: err.message ?? 'Token inválido' });
      throw err;
    }
  },

  logout: async () => {
    try { await api.post('/api/v1/public/account/logout/'); } catch {}
    await setToken(null);
    set({ participante: null });
  },

  refresh: async () => {
    try {
      const me = await api.get<Participant>('/api/v1/public/account/me/');
      set({ participante: me, ready: true });
    } catch {
      // token inválido o expirado → logout silencioso
      await setToken(null);
      set({ participante: null, ready: true });
    }
  },

  clearError: () => set({ error: null }),
}));
