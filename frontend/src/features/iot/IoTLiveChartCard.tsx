"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { listDevices, getDeviceReadings, type IoTDevice, type IoTReading } from "@/features/iot/api";

const IOT_CATEGORY_LABELS: Record<string, string> = {
  energie: "Énergie",
  eau: "Eau",
  dechets: "Déchets",
  emissions: "Émissions",
  ambiance: "Ambiance",
};

const IOT_CATEGORY_COLORS: Record<string, string> = {
  energie: "#00A651",
  eau: "#3D7AA8",
  dechets: "#C98A2C",
  emissions: "#B5473A",
  ambiance: "#7A5FC9",
};

const REFRESH_MS = 10000;
const POINTS_LIMIT = 50;

function categoryColor(category?: string) {
  return (category && IOT_CATEGORY_COLORS[category]) || "#00A651";
}

export default function IoTLiveChartCard({ siteId }: { siteId?: string }) {
  const [devices, setDevices] = useState<IoTDevice[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [readings, setReadings] = useState<IoTReading[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);

  useEffect(() => {
    setLoading(true);
    listDevices(siteId)
      .then((all) => {
        const active = all.filter((d) => d.status === "active");
        setDevices(active);
        setSelectedId((prev) => prev ?? active[0]?.id ?? null);
      })
      .finally(() => setLoading(false));
  }, [siteId]);

  const loadReadings = useCallback(async (deviceId: string) => {
    try {
      const data = await getDeviceReadings(deviceId, POINTS_LIMIT);
      setReadings(data);
    } catch {
      // on garde le dernier état connu en cas d'erreur ponctuelle
    }
  }, []);

  // Recharge immédiatement dès que selectedId change (clic dans le sélecteur),
  // puis toutes les 10s tant que ce capteur reste sélectionné.
  useEffect(() => {
    if (!selectedId) return;
    setReadings([]); // vide l'ancienne courbe tout de suite, avant même la réponse
    loadReadings(selectedId);
    const interval = setInterval(() => loadReadings(selectedId), REFRESH_MS);
    return () => clearInterval(interval);
  }, [selectedId, loadReadings]);

  async function handleSync() {
    if (!selectedId || syncing) return;
    setSyncing(true);
    await loadReadings(selectedId);
    setSyncing(false);
  }

  function handleSelectChange(e: React.ChangeEvent<HTMLSelectElement>) {
    setSelectedId(e.target.value);
  }

  const selectedDevice = devices.find((d) => d.id === selectedId);
  const color = categoryColor(selectedDevice?.category);

  const chartData = readings
    .slice()
    .reverse()
    .map((r) => ({
      time: new Date(r.timestamp).toLocaleTimeString("fr-FR", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      }),
      value: r.value,
    }));

  const latest = readings[0];

  if (loading) {
    return (
      <div className="mb-5 rounded-xl border border-[#DCE8E0] bg-white p-5">
        <div className="h-4 w-32 animate-pulse rounded bg-[#EEF3EF]" />
        <div className="mt-3 h-6 w-48 animate-pulse rounded bg-[#EEF3EF]" />
        <div className="mt-5 h-[220px] w-full animate-pulse rounded-lg bg-[#F5F8F6]" />
      </div>
    );
  }

  if (devices.length === 0) {
    return null;
  }

  return (
    <div className="mb-5 overflow-hidden rounded-xl border border-[#DCE8E0] bg-white shadow-[0_1px_2px_rgba(11,107,58,0.04)]">
      <div className="flex items-start justify-between border-b border-[#F0F3F1] px-5 py-4">
        <div>
          <div className="flex items-center gap-1.5">
            <span
              className="h-1.5 w-1.5 rounded-full"
              style={{ backgroundColor: color }}
            />
            <span className="text-[11px] font-semibold uppercase tracking-wide text-[#5A6F62]">
              {selectedDevice
                ? IOT_CATEGORY_LABELS[selectedDevice.category] ?? selectedDevice.category
                : "Capteur IoT"}
            </span>
            <span className="ml-1.5 flex items-center gap-1 rounded-full bg-[#E8F7EE] px-2 py-0.5 text-[10px] font-semibold text-[#0B6B3A]">
              <span className="relative flex h-1.5 w-1.5">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#00A651] opacity-60" />
                <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-[#00A651]" />
              </span>
              En direct
            </span>
          </div>

          {/* Sélecteur natif : fiable à 100%, aucun bug de clic/overlay possible */}
          <select
            value={selectedId ?? ""}
            onChange={handleSelectChange}
            className="mt-1.5 cursor-pointer rounded-lg border border-[#DCE8E0] bg-white px-2.5 py-1.5 text-[15px] font-bold text-[#1A2E22] outline-none transition hover:border-[#7BC99A] focus:border-[#00A651]"
          >
            {devices.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name} — {IOT_CATEGORY_LABELS[d.category] ?? d.category}
              </option>
            ))}
          </select>
        </div>

        {latest && (
          <div className="text-right">
            <div className="text-[26px] font-bold leading-none text-[#1A2E22]">
              {latest.value.toLocaleString("fr-FR", { maximumFractionDigits: 2 })}
              <span className="ml-1 text-sm font-semibold text-[#5A6F62]">
                {selectedDevice?.unit}
              </span>
            </div>
            <div className="mt-1.5 text-[11px] text-[#5A6F62]">
              Mis à jour à {new Date(latest.timestamp).toLocaleTimeString("fr-FR")}
            </div>
          </div>
        )}
      </div>

      <div className="px-3 pb-3 pt-3">
        <div className="mb-2 flex items-center justify-between px-2">
          <span className="text-[11px] text-[#8A9992]">
            Actualisation automatique toutes les 10s
          </span>
          <button
            type="button"
            onClick={handleSync}
            disabled={syncing}
            className="flex items-center gap-1.5 rounded-lg border border-[#DCE8E0] px-2.5 py-1.5 text-xs font-medium text-[#5A6F62] transition hover:border-[#7BC99A] hover:bg-[#F0F9F3] hover:text-[#0B6B3A] disabled:cursor-not-allowed disabled:opacity-60"
          >
            <svg
              width="13"
              height="13"
              viewBox="0 0 20 20"
              fill="none"
              className={syncing ? "animate-spin" : ""}
            >
              <path
                d="M16.5 10a6.5 6.5 0 10-2.1 4.8M16.5 10V5.5M16.5 10h-4.5"
                stroke="currentColor"
                strokeWidth="1.7"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            {syncing ? "Synchronisation…" : "Synchroniser"}
          </button>
        </div>

        {chartData.length === 0 ? (
          <div className="flex h-[220px] items-center justify-center text-sm text-[#5A6F62]">
            En attente de mesures…
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={chartData} margin={{ top: 4, right: 12, left: -12, bottom: 0 }}>
              <defs>
                <linearGradient id="iotChartFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={color} stopOpacity={0.22} />
                  <stop offset="100%" stopColor={color} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#EEF2EF" vertical={false} />
              <XAxis
                dataKey="time"
                tick={{ fontSize: 11, fill: "#8A9992" }}
                axisLine={{ stroke: "#E8EEE9" }}
                tickLine={false}
                minTickGap={40}
              />
              <YAxis
                tick={{ fontSize: 11, fill: "#8A9992" }}
                axisLine={false}
                tickLine={false}
                width={38}
              />
              <Tooltip
                contentStyle={{
                  borderRadius: 10,
                  border: "1px solid #E8EEE9",
                  boxShadow: "0 4px 16px rgba(11,107,58,0.08)",
                  fontSize: 12.5,
                }}
                labelStyle={{ color: "#5A6F62", fontWeight: 600 }}
                formatter={(value: number) => [
                  `${value.toLocaleString("fr-FR", { maximumFractionDigits: 2 })} ${selectedDevice?.unit ?? ""}`,
                  selectedDevice?.name ?? "Valeur",
                ]}
              />
              <Area
                type="monotone"
                dataKey="value"
                stroke={color}
                strokeWidth={2.25}
                fill="url(#iotChartFill)"
                dot={false}
                activeDot={{ r: 4, strokeWidth: 0 }}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
