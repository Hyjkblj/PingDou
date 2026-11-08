import { create } from 'zustand';
import type { AuthSession, User } from '../api/types';

type AuthState = {
  user: User | null;
  isAuthenticated: boolean;
  setSession: (session: AuthSession) => void;
  logout: () => void;
};

const savedUser = localStorage.getItem('pingdou_user');

export const useAuthStore = create<AuthState>((set) => ({
  user: savedUser ? JSON.parse(savedUser) : null,
  isAuthenticated: Boolean(localStorage.getItem('pingdou_access_token')),
  setSession: (session) => {
    localStorage.setItem('pingdou_access_token', session.accessToken);
    localStorage.setItem('pingdou_refresh_token', session.refreshToken);
    localStorage.setItem('pingdou_user', JSON.stringify(session.user));
    set({ user: session.user, isAuthenticated: true });
  },
  logout: () => {
    localStorage.removeItem('pingdou_access_token');
    localStorage.removeItem('pingdou_refresh_token');
    localStorage.removeItem('pingdou_user');
    set({ user: null, isAuthenticated: false });
  },
}));
