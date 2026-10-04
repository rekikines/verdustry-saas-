import { getAccessToken } from "@/features/auth/storage";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export type DataSource = {
  id: string;
  name: string;
  type: string;
  category: string;
  status: string;
  volume: string | null;
  site_id: string;
  company_id: string;
  last_sync_at: string | null;
  created_at?: string | null;
};

export type ConnectionType = {
  type: string;
  label: string;
  primary?: boolean;
  description?: string;
};

function headers(): HeadersInit {
  const token = getAccessToken();
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

export async function fetchConnectionTypes(): Promise<ConnectionType[]> {
  const r = await fetch(`${API_URL}/api/sources/connection-types`);
  if (!r.ok) throw new Error("Types indisponibles");
  return r.json();
}

export async function fetchSources(siteId?: string): Promise<DataSource[]> {
  const q = siteId ? `?site_id=${encodeURIComponent(siteId)}` : "";
  const r = await fetch(`${API_URL}/api/sources${q}`, { headers: headers() });
  if (!r.ok) throw new Error("Impossible de charger les sources");
  return r.json();
}

export async function createSource(body: {
  name: string;
  type: string;
  category: string;
  site_id: string;
  config?: Record<string, string | string[]>;   // ← élargi
}): Promise<DataSource> {
  const r = await fetch(`${API_URL}/api/sources`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify(body),
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || "Création impossible");
  return data;
}

export async function syncSource(id: string): Promise<DataSource> {
  const r = await fetch(`${API_URL}/api/sources/${id}/sync`, {
    method: "POST",
    headers: headers(),
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || "Sync impossible");
  return data;
}

export async function deleteSource(id: string): Promise<void> {
  const r = await fetch(`${API_URL}/api/sources/${id}`, {
    method: "DELETE",
    headers: headers(),
  });
  if (!r.ok) throw new Error("Suppression impossible");
}