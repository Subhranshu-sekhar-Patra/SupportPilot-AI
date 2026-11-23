/**
 * SupportPilot AI — Axios API Client
 * Handles authentication headers, token refresh, and error normalization.
 */

import axios, { AxiosError, type AxiosInstance } from "axios";
import type { APIError } from "@/types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ── Token storage ──────────────────────────────────────────
const TOKEN_KEY = "sp_access_token";
const REFRESH_KEY = "sp_refresh_token";

export const tokenStore = {
  getAccess: () =>
    typeof window !== "undefined" ? localStorage.getItem(TOKEN_KEY) : null,
  getRefresh: () =>
    typeof window !== "undefined" ? localStorage.getItem(REFRESH_KEY) : null,
  set: (access: string, refresh: string) => {
    localStorage.setItem(TOKEN_KEY, access);
    localStorage.setItem(REFRESH_KEY, refresh);
  },
  clear: () => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
};

// ── Create axios instance ──────────────────────────────────
export const apiClient: AxiosInstance = axios.create({
  baseURL: `${BASE_URL}/api/v1`,
  headers: { "Content-Type": "application/json" },
  timeout: 30_000,
});

// ── Request interceptor — attach token ─────────────────────
apiClient.interceptors.request.use((config) => {
  const token = tokenStore.getAccess();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ── Response interceptor — handle 401 / token refresh ──────
let isRefreshing = false;
let refreshSubscribers: ((token: string) => void)[] = [];

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<APIError>) => {
    const originalRequest = error.config as typeof error.config & {
      _retry?: boolean;
    };

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      if (isRefreshing) {
        // Queue the request until refresh completes
        return new Promise((resolve) => {
          refreshSubscribers.push((token) => {
            originalRequest.headers!.Authorization = `Bearer ${token}`;
            resolve(apiClient(originalRequest));
          });
        });
      }

      isRefreshing = true;
      const refreshToken = tokenStore.getRefresh();

      if (!refreshToken) {
        tokenStore.clear();
        window.location.href = "/login";
        return Promise.reject(error);
      }

      try {
        const { data } = await axios.post(`${BASE_URL}/api/v1/auth/refresh`, {
          refresh_token: refreshToken,
        });
        tokenStore.set(data.access_token, data.refresh_token);

        // Notify queued requests
        refreshSubscribers.forEach((cb) => cb(data.access_token));
        refreshSubscribers = [];

        originalRequest.headers!.Authorization = `Bearer ${data.access_token}`;
        return apiClient(originalRequest);
      } catch {
        tokenStore.clear();
        window.location.href = "/login";
        return Promise.reject(error);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

export default apiClient;
