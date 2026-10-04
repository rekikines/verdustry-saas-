import { getAccessToken } from "@/features/auth/storage";
import type { Extraction } from "@/features/validation/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export async function ocrStatus(): Promise<{ available: boolean; engine: string }> {
  const r = await fetch(`${API_URL}/api/ocr/status`);
  if (!r.ok) return { available: false, engine: "unknown" };
  return r.json();
}

export async function extractDocument(params: {
  file: File;
  siteId: string;
}): Promise<Extraction> {
  const token = getAccessToken();
  const form = new FormData();
  form.append("file", params.file);
  form.append("site_id", params.siteId);

  const r = await fetch(`${API_URL}/api/ocr/extract`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: form,
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) {
    const msg =
      typeof data.detail === "string" ? data.detail : "Extraction impossible";
    throw new Error(msg);
  }
  return data;
}