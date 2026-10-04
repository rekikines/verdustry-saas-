import { getAccessToken } from "@/features/auth/storage";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export type CategoryBreakdown = {
  category: string;
  sources_count: number;
  active_sources_count: number;
  records_count: number;
};

export type IoTDeviceStat = {
  device_id: string;
  device_name: string;
  category: string;
  latest_value: number | null;
  latest_unit: string | null;
  latest_timestamp: string | null;
};

export type DashboardStats = {
  total_sources: number;
  active_sources: number;
  ocr_pending_sources: number;
  pending_validation: number;
  sites_count: number;
  category_breakdown: CategoryBreakdown[];
  iot_devices: IoTDeviceStat[];
};

export async function fetchDashboardStats(): Promise<DashboardStats> {
  const token = getAccessToken();
  const r = await fetch(`${API_URL}/api/dashboard/stats`, {
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });
  if (!r.ok) throw new Error("Impossible de charger les statistiques");
  return r.json();
}