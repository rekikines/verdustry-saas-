import { getAccessToken } from "@/features/auth/storage";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export type Site = {
  id: string;
  name: string;
  location: string | null;
  company_id: string;
};

function authHeaders(): HeadersInit {
  const token = getAccessToken();
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

export async function fetchSites(): Promise<Site[]> {
  const r = await fetch(`${API_URL}/api/sites`, { headers: authHeaders() });
  if (!r.ok) throw new Error("Impossible de charger les sites");
  return r.json();
}

export async function createSite(body: {
  name: string;
  location?: string;
}): Promise<Site> {
  const r = await fetch(`${API_URL}/api/sites`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(body),
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || "Création impossible");
  return data;
}

export async function updateSite(
  id: string,
  body: { name?: string; location?: string }
): Promise<Site> {
  const r = await fetch(`${API_URL}/api/sites/${id}`, {
    method: "PATCH",
    headers: authHeaders(),
    body: JSON.stringify(body),
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || "Mise à jour impossible");
  return data;
}

export async function deleteSite(id: string): Promise<void> {
  const r = await fetch(`${API_URL}/api/sites/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!r.ok) {
    const data = await r.json().catch(() => ({}));
    throw new Error(data.detail || "Suppression impossible");
  }
}