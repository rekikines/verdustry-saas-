import { getAccessToken } from "@/features/auth/storage";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export type Extraction = {
  id: string;
  filename: string;
  doc_type: string;
  category: string;
  status: string;
  confidence: number;
  fields: Record<string, string> | null;
  source_id: string | null;
  site_id: string;
  company_id: string;
  created_at?: string | null;
};

function headers(): HeadersInit {
  const token = getAccessToken();
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

export async function fetchPending(): Promise<Extraction[]> {
  const r = await fetch(`${API_URL}/api/validation?status=PENDING`, {
    headers: headers(),
  });
  if (!r.ok) throw new Error("Impossible de charger les validations");
  return r.json();
}

export async function validateExtraction(id: string): Promise<Extraction> {
  const r = await fetch(`${API_URL}/api/validation/${id}/validate`, {
    method: "POST",
    headers: headers(),
  });
  if (!r.ok) throw new Error("Validation échouée");
  return r.json();
}

export async function rejectExtraction(id: string): Promise<Extraction> {
  const r = await fetch(`${API_URL}/api/validation/${id}/reject`, {
    method: "POST",
    headers: headers(),
  });
  if (!r.ok) throw new Error("Rejet échoué");
  return r.json();
}

export async function updateFields(
  id: string,
  fields: Record<string, string>
): Promise<Extraction> {
  const r = await fetch(`${API_URL}/api/validation/${id}/fields`, {
    method: "PATCH",
    headers: headers(),
    body: JSON.stringify({ fields }),
  });
  if (!r.ok) throw new Error("Mise à jour échouée");
  return r.json();
}

export async function seedDemo(): Promise<Extraction[]> {
  const r = await fetch(`${API_URL}/api/validation/seed-demo`, {
    method: "POST",
    headers: headers(),
  });
  if (!r.ok) throw new Error("Seed impossible");
  return r.json();
}