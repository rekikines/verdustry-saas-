import type { AuthUser, RegisterPayload, TokenResponse } from "./types";
import { clearAuth, getAccessToken, saveAuth } from "./storage";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export async function register(payload: RegisterPayload): Promise<TokenResponse> {
  const r = await fetch(`${API_URL}/api/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) {
    const msg =
      typeof data.detail === "string"
        ? data.detail
        : "Inscription impossible";
    throw new Error(msg);
  }
  saveAuth(data as TokenResponse);
  return data as TokenResponse;
}

export async function login(email: string, password: string): Promise<TokenResponse> {
  const r = await fetch(`${API_URL}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) {
    const msg =
      typeof data.detail === "string"
        ? data.detail
        : "Email ou mot de passe incorrect";
    throw new Error(msg);
  }
  saveAuth(data as TokenResponse);
  return data as TokenResponse;
}

export async function fetchMe(): Promise<AuthUser> {
  const token = getAccessToken();
  if (!token) throw new Error("Non connecté");

  const r = await fetch(`${API_URL}/api/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!r.ok) {
    clearAuth();
    throw new Error("Session expirée");
  }
  return r.json();
}

export function logout() {
  clearAuth();
}