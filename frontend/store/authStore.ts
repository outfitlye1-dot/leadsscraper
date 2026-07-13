import { create } from "zustand";
import { persist } from "zustand/middleware";
import api from "@/lib/api";
import { removeToken, setToken } from "@/lib/auth";
import type { TokenResponse, User } from "@/lib/types";

type OtpPurpose = "login" | "register" | "reset_password";

interface OtpSendResponse {
  message: string;
  expires_in_minutes: number;
}

interface AuthState {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<void>;
  sendOtp: (email: string, purpose: OtpPurpose) => Promise<OtpSendResponse>;
  verifyOtp: (
    email: string,
    code: string,
    purpose: OtpPurpose,
    name?: string,
    password?: string
  ) => Promise<void>;
  logout: () => void;
  fetchUser: () => Promise<void>;
  setUser: (user: User | null) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      isLoading: false,
      isAuthenticated: false,

      login: async (email, password) => {
        set({ isLoading: true });
        try {
          const { data } = await api.post<TokenResponse>("/auth/login", {
            email,
            password,
          });
          setToken(data.access_token);
          await get().fetchUser();
        } finally {
          set({ isLoading: false });
        }
      },

      register: async (name, email, password) => {
        set({ isLoading: true });
        try {
          await api.post("/auth/register", { name, email, password });
          await get().login(email, password);
        } finally {
          set({ isLoading: false });
        }
      },

      sendOtp: async (email, purpose) => {
        set({ isLoading: true });
        try {
          const { data } = await api.post<OtpSendResponse>("/auth/otp/send", {
            email,
            purpose,
          });
          return data;
        } finally {
          set({ isLoading: false });
        }
      },

      verifyOtp: async (email, code, purpose, name, password) => {
        set({ isLoading: true });
        try {
          const { data } = await api.post<TokenResponse>("/auth/otp/verify", {
            email,
            code,
            purpose,
            ...(name ? { name } : {}),
            ...(password ? { password } : {}),
          });
          setToken(data.access_token);
          await get().fetchUser();
        } finally {
          set({ isLoading: false });
        }
      },

      logout: () => {
        void api.post("/scraper/background/stop").catch(() => undefined);
        removeToken();
        set({ user: null, isAuthenticated: false });
      },

      fetchUser: async () => {
        try {
          const { data } = await api.get<User>("/auth/me");
          set({ user: data, isAuthenticated: true });
        } catch {
          removeToken();
          set({ user: null, isAuthenticated: false });
        }
      },

      setUser: (user) => set({ user, isAuthenticated: !!user }),
    }),
    {
      name: "leadgen-auth",
      partialize: (state) => ({ user: state.user, isAuthenticated: state.isAuthenticated }),
    }
  )
);
