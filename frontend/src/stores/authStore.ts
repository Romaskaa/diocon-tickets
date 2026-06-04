import { create } from 'zustand';
import { authApi } from '@/api/client';
import type { User } from '@/types';

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  fetchUser: () => Promise<void>;
  setUser: (user: User) => void;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: (() => {
    try {
      const stored = localStorage.getItem('user');
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  })(),
  isAuthenticated: !!localStorage.getItem('access_token'),
  isLoading: false,
  error: null,

  login: async (email: string, password: string) => {
    set({ isLoading: true, error: null });
    try {
      const tokens = await authApi.login(email, password);
      
      // Сохраняем токены
      localStorage.setItem('access_token', tokens.access_token);
      localStorage.setItem('refresh_token', tokens.refresh_token);
      
      // Также в cookies
      document.cookie = `access_token=${tokens.access_token}; path=/; max-age=${tokens.expires_at}`;
      document.cookie = `refresh_token=${tokens.refresh_token}; path=/; max-age=2592000`;
      
      // Получаем пользователя
      const user = await authApi.getMe();
      localStorage.setItem('user', JSON.stringify(user));
      
      set({ user, isAuthenticated: true, isLoading: false });
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Ошибка входа';
      set({ error: message, isLoading: false });
      throw error;
    }
  },

  logout: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    document.cookie = 'access_token=; path=/; max-age=0';
    document.cookie = 'refresh_token=; path=/; max-age=0';
    set({ user: null, isAuthenticated: false });
  },

  fetchUser: async () => {
    if (!localStorage.getItem('access_token')) {
      set({ user: null, isAuthenticated: false });
      return;
    }
    
    set({ isLoading: true });
    try {
      const user = await authApi.getMe();
      // Сохраняем avatar_url если он есть в localStorage
      const storedUser = localStorage.getItem('user');
      if (storedUser) {
        const parsed = JSON.parse(storedUser);
        if (parsed.avatar_url && !user.avatar_url) {
          user.avatar_url = parsed.avatar_url;
        }
      }
      localStorage.setItem('user', JSON.stringify(user));
      set({ user, isAuthenticated: true, isLoading: false });
    } catch {
      get().logout();
      set({ isLoading: false });
    }
  },

  setUser: (user: User) => {
    localStorage.setItem('user', JSON.stringify(user));
    set({ user });
  },

  clearError: () => set({ error: null }),
}));
