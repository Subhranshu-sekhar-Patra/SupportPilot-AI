/**
 * SupportPilot AI — Zustand Auth Store
 */

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import type { User, AuthTokens } from "@/types";
import { tokenStore } from "@/lib/api";

const DEMO_USER: User = {
  id: "usr_alex_turner_demo",
  email: "alex.turner@supportpilot.io",
  full_name: "Alex Turner",
  role: "admin",
  is_active: true,
  is_verified: true,
  organization: {
    id: "org_acme_corp",
    name: "Acme Cloud Technologies",
    slug: "acme-cloud",
    plan: "Enterprise Scale",
  },
};

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;

  setAuth: (user: User, tokens: AuthTokens) => void;
  loginAsDemo: () => void;
  clearAuth: () => void;
  setLoading: (loading: boolean) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: DEMO_USER,
      isAuthenticated: true,
      isLoading: false,

      setAuth: (user, tokens) => {
        tokenStore.set(tokens.access_token, tokens.refresh_token);
        set({ user, isAuthenticated: true, isLoading: false });
      },

      loginAsDemo: () => {
        set({ user: DEMO_USER, isAuthenticated: true, isLoading: false });
      },

      clearAuth: () => {
        tokenStore.clear();
        set({ user: null, isAuthenticated: false });
      },

      setLoading: (loading) => set({ isLoading: loading }),
    }),
    {
      name: "sp-auth-v2",
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({ user: state.user, isAuthenticated: state.isAuthenticated }),
    }
  )
);
