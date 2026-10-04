// src/features/iot/api.ts
//
// Client API du module IoT — même pattern que src/features/sources/api.ts
// (fetch direct, pas de wrapper partagé, token géré via getAccessToken()).

import { getAccessToken } from "@/features/auth/storage";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export type IoTCategory = "energie" | "eau" | "dechets" | "emissions" | "ambiance";
export type IoTProtocol = "modbus_rtu" | "modbus_tcp" | "mqtt" | "lorawan" | "http" | "simulator";
export type IoTDeviceStatus = "active" | "inactive" | "error";
export type IoTQualityFlag = "ok" | "out_of_range" | "duplicate" | "gap_filled";
export type IoTAlertType = "offline" | "out_of_range" | "threshold_exceeded";

export interface IoTDevice {
  id: string;
  site_id: string;
  gateway_id: string | null;
  data_source_id: string | null;
  device_uid: string;
  name: string;
  device_type: string;
  category: IoTCategory;
  protocol: IoTProtocol;
  unit: string;
  status: IoTDeviceStatus;
  last_seen_at: string | null;
  min_valid_value: number | null;
  max_valid_value: number | null;
  alert_threshold: number | null;
  created_at: string;
}

export interface IoTDeviceCreate {
  site_id: string;
  gateway_id?: string | null;
  data_source_id?: string | null;
  device_uid: string;
  name: string;
  device_type: string;
  category: IoTCategory;
  protocol: IoTProtocol;
  connection_params?: Record<string, unknown>;
  unit: string;
  min_valid_value?: number | null;
  max_valid_value?: number | null;
  alert_threshold?: number | null;
}

export interface IoTReading {
  id: string;
  device_id: string;
  timestamp: string;
  value: number;
  quality_flag: IoTQualityFlag;
}

export interface IoTAlert {
  id: string;
  device_id: string;
  type: IoTAlertType;
  message: string;
  created_at: string;
  resolved_at: string | null;
}

export interface IoTGateway {
  id: string;
  site_id: string;
  name: string;
  status: "online" | "offline" | "degraded";
  last_heartbeat_at: string | null;
  created_at: string;
}

function headers(): HeadersInit {
  const token = getAccessToken();
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

// ---------------------------------------------------------------------------
// Devices
// ---------------------------------------------------------------------------

export async function listDevices(siteId?: string): Promise<IoTDevice[]> {
  const q = siteId ? `?site_id=${encodeURIComponent(siteId)}` : "";
  const r = await fetch(`${API_URL}/api/iot/devices${q}`, { headers: headers() });
  if (!r.ok) throw new Error("Impossible de charger les capteurs");
  return r.json();
}

export async function getDevice(deviceId: string): Promise<IoTDevice> {
  const r = await fetch(`${API_URL}/api/iot/devices/${deviceId}`, { headers: headers() });
  if (!r.ok) throw new Error("Capteur introuvable");
  return r.json();
}

export async function createDevice(payload: IoTDeviceCreate): Promise<IoTDevice> {
  const r = await fetch(`${API_URL}/api/iot/devices`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify(payload),
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || "Création du capteur impossible");
  return data;
}

export async function getDeviceReadings(deviceId: string, limit = 100): Promise<IoTReading[]> {
  const r = await fetch(`${API_URL}/api/iot/devices/${deviceId}/readings?limit=${limit}`, {
    headers: headers(),
  });
  if (!r.ok) throw new Error("Impossible de charger les mesures");
  return r.json();
}

// ---------------------------------------------------------------------------
// Gateways
// ---------------------------------------------------------------------------

export async function listGateways(siteId?: string): Promise<IoTGateway[]> {
  const q = siteId ? `?site_id=${encodeURIComponent(siteId)}` : "";
  const r = await fetch(`${API_URL}/api/iot/gateways${q}`, { headers: headers() });
  if (!r.ok) throw new Error("Impossible de charger les gateways");
  return r.json();
}

export async function createGateway(payload: { site_id: string; name: string }): Promise<IoTGateway> {
  const r = await fetch(`${API_URL}/api/iot/gateways`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify(payload),
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || "Création de la gateway impossible");
  return data;
}

// ---------------------------------------------------------------------------
// Alerts
// ---------------------------------------------------------------------------

export async function listAlerts(deviceId?: string): Promise<IoTAlert[]> {
  const q = deviceId ? `?device_id=${encodeURIComponent(deviceId)}` : "";
  const r = await fetch(`${API_URL}/api/iot/alerts${q}`, { headers: headers() });
  if (!r.ok) throw new Error("Impossible de charger les alertes");
  return r.json();
}
