import type { AuthUser, TokenResponse } from "./types";

const KEYS = {
  access: "verdustry_access",
  refresh: "verdustry_refresh",
  user: "verdustry_user",
};

export function saveAuth(data: TokenResponse) {
  localStorage.setItem(KEYS.access, data.access_token);
  localStorage.setItem(KEYS.refresh, data.refresh_token);
  localStorage.setItem(KEYS.user, JSON.stringify(data.user));
}

export function clearAuth() {
  localStorage.removeItem(KEYS.access);
  localStorage.removeItem(KEYS.refresh);
  localStorage.removeItem(KEYS.user);
}

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(KEYS.access);
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(KEYS.refresh);
}

export function getStoredUser(): AuthUser | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(KEYS.user);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AuthUser;
  } catch {
    return null;
  }
}