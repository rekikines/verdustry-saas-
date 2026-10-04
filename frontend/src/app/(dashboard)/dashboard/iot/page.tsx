// src/app/(dashboard)/dashboard/iot/page.tsx
//
// Écran de gestion des capteurs IoT — même structure que vos pages
// sites/sources existantes (dossier (dashboard)/dashboard/<module>/page.tsx).

"use client";

import { useEffect, useState } from "react";
import {
  listDevices,
  createDevice,
  getDeviceReadings,
  listAlerts,
  type IoTDevice,
  type IoTDeviceCreate,
  type IoTReading,
  type IoTAlert,
  type IoTCategory,
  type IoTProtocol,
} from "@/features/iot/api";

const CATEGORIES: IoTCategory[] = ["energie", "eau", "dechets", "emissions", "ambiance"];
const PROTOCOLS: IoTProtocol[] = ["simulator", "modbus_rtu", "modbus_tcp", "mqtt", "lorawan", "http"];

const DEVICE_TYPE_PRESETS: Record<string, { category: IoTCategory; unit: string }> = {
  energy_meter: { category: "energie", unit: "kWh" },
  water_flow: { category: "eau", unit: "m3" },
  co2: { category: "emissions", unit: "ppm" },
  pm25: { category: "emissions", unit: "µg/m3" },
  waste_level: { category: "dechets", unit: "%" },
  weight: { category: "dechets", unit: "kg" },
};

export default function IoTPage() {
  const [devices, setDevices] = useState<IoTDevice[]>([]);
  const [alerts, setAlerts] = useState<IoTAlert[]>([]);
  const [selectedDevice, setSelectedDevice] = useState<IoTDevice | null>(null);
  const [readings, setReadings] = useState<IoTReading[]>([]);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [loading, setLoading] = useState(true);

  async function refresh() {
    setLoading(true);
    try {
      const [devicesData, alertsData] = await Promise.all([listDevices(), listAlerts()]);
      setDevices(devicesData);
      setAlerts(alertsData);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  useEffect(() => {
    if (!selectedDevice) return;
    getDeviceReadings(selectedDevice.id, 50).then(setReadings);
    const interval = setInterval(() => {
      getDeviceReadings(selectedDevice.id, 50).then(setReadings);
    }, 5000); // rafraîchit toutes les 5s — utile pour voir arriver le test en direct
    return () => clearInterval(interval);
  }, [selectedDevice]);

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Capteurs IoT</h1>
          <p className="text-sm text-gray-500">
            Supervision des capteurs environnementaux connectés (énergie, eau, déchets, émissions).
          </p>
        </div>
        <button
          onClick={() => setShowCreateForm(true)}
          className="rounded-md bg-green-700 px-4 py-2 text-sm font-medium text-white hover:bg-green-800"
        >
          + Ajouter un capteur
        </button>
      </div>

      {alerts.length > 0 && (
        <div className="rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-800">
          {alerts.length} alerte(s) active(s) — {alerts.slice(0, 3).map((a) => a.message).join(" · ")}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Liste des devices */}
        <div className="lg:col-span-1 border rounded-lg divide-y">
          {loading && <div className="p-4 text-sm text-gray-500">Chargement...</div>}
          {!loading && devices.length === 0 && (
            <div className="p-4 text-sm text-gray-500">Aucun capteur pour le moment.</div>
          )}
          {devices.map((device) => (
            <button
              key={device.id}
              onClick={() => setSelectedDevice(device)}
              className={`w-full text-left p-4 hover:bg-gray-50 ${
                selectedDevice?.id === device.id ? "bg-green-50" : ""
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-medium">{device.name}</span>
                <StatusBadge status={device.status} />
              </div>
              <div className="text-xs text-gray-500 mt-1">
                {device.category} · {device.protocol} · {device.device_uid}
              </div>
              {device.last_seen_at && (
                <div className="text-xs text-gray-400 mt-1">
                  Dernière donnée : {new Date(device.last_seen_at).toLocaleString("fr-FR")}
                </div>
              )}
            </button>
          ))}
        </div>

        {/* Détail + lectures récentes */}
        <div className="lg:col-span-2 border rounded-lg p-4">
          {!selectedDevice && (
            <div className="text-sm text-gray-500">Sélectionnez un capteur pour voir ses dernières mesures.</div>
          )}
          {selectedDevice && (
            <div>
              <h2 className="text-lg font-semibold mb-1">{selectedDevice.name}</h2>
              <p className="text-sm text-gray-500 mb-4">
                {selectedDevice.device_type} — unité : {selectedDevice.unit} — device_uid :{" "}
                <code className="bg-gray-100 px-1 rounded">{selectedDevice.device_uid}</code>
              </p>

              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-gray-500 border-b">
                    <th className="py-2">Horodatage</th>
                    <th className="py-2">Valeur</th>
                    <th className="py-2">Qualité</th>
                  </tr>
                </thead>
                <tbody>
                  {readings.map((r) => (
                    <tr key={r.id} className="border-b last:border-0">
                      <td className="py-2">{new Date(r.timestamp).toLocaleString("fr-FR")}</td>
                      <td className="py-2 font-medium">
                        {r.value} {selectedDevice.unit}
                      </td>
                      <td className="py-2">
                        <QualityBadge flag={r.quality_flag} />
                      </td>
                    </tr>
                  ))}
                  {readings.length === 0 && (
                    <tr>
                      <td colSpan={3} className="py-4 text-center text-gray-400">
                        Aucune mesure reçue pour ce capteur pour le moment.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {showCreateForm && (
        <CreateDeviceModal
          onClose={() => setShowCreateForm(false)}
          onCreated={() => {
            setShowCreateForm(false);
            refresh();
          }}
        />
      )}
    </div>
  );
}

function StatusBadge({ status }: { status: IoTDevice["status"] }) {
  const styles: Record<string, string> = {
    active: "bg-green-100 text-green-700",
    inactive: "bg-gray-100 text-gray-600",
    error: "bg-red-100 text-red-700",
  };
  const labels: Record<string, string> = { active: "Actif", inactive: "Inactif", error: "Hors ligne" };
  return <span className={`text-xs px-2 py-0.5 rounded-full ${styles[status]}`}>{labels[status]}</span>;
}

function QualityBadge({ flag }: { flag: IoTReading["quality_flag"] }) {
  if (flag === "ok") return <span className="text-xs text-green-700">OK</span>;
  if (flag === "out_of_range") return <span className="text-xs text-red-700">Hors plage</span>;
  return <span className="text-xs text-gray-500">{flag}</span>;
}

function CreateDeviceModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [form, setForm] = useState<IoTDeviceCreate>({
    site_id: "",
    device_uid: "",
    name: "",
    device_type: "energy_meter",
    category: "energie",
    protocol: "simulator",
    unit: "kWh",
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function handleDeviceTypeChange(deviceType: string) {
    const preset = DEVICE_TYPE_PRESETS[deviceType];
    setForm((f) => ({
      ...f,
      device_type: deviceType,
      category: preset?.category ?? f.category,
      unit: preset?.unit ?? f.unit,
    }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await createDevice(form);
      onCreated();
    } catch (err) {
      setError("Erreur lors de la création du capteur. Vérifiez les champs.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <form onSubmit={handleSubmit} className="bg-white rounded-lg p-6 w-full max-w-md space-y-4">
        <h2 className="text-lg font-semibold">Ajouter un capteur IoT</h2>

        <div>
          <label className="block text-sm mb-1">Site (site_id)</label>
          <input
            required
            className="w-full border rounded px-3 py-2 text-sm"
            value={form.site_id}
            onChange={(e) => setForm({ ...form, site_id: e.target.value })}
            placeholder="site-xxxxxxxx"
          />
        </div>

        <div>
          <label className="block text-sm mb-1">Nom du capteur</label>
          <input
            required
            className="w-full border rounded px-3 py-2 text-sm"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            placeholder="Compteur électrique atelier 1"
          />
        </div>

        <div>
          <label className="block text-sm mb-1">Identifiant matériel (device_uid)</label>
          <input
            required
            className="w-full border rounded px-3 py-2 text-sm"
            value={form.device_uid}
            onChange={(e) => setForm({ ...form, device_uid: e.target.value })}
            placeholder="sim-energy-site1"
          />
          <p className="text-xs text-gray-400 mt-1">
            Doit correspondre exactement au device_uid envoyé par la gateway / le simulateur.
          </p>
        </div>

        <div>
          <label className="block text-sm mb-1">Type de capteur</label>
          <select
            className="w-full border rounded px-3 py-2 text-sm"
            value={form.device_type}
            onChange={(e) => handleDeviceTypeChange(e.target.value)}
          >
            {Object.keys(DEVICE_TYPE_PRESETS).map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-sm mb-1">Catégorie</label>
            <select
              className="w-full border rounded px-3 py-2 text-sm"
              value={form.category}
              onChange={(e) => setForm({ ...form, category: e.target.value as IoTCategory })}
            >
              {CATEGORIES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm mb-1">Unité</label>
            <input
              className="w-full border rounded px-3 py-2 text-sm"
              value={form.unit}
              onChange={(e) => setForm({ ...form, unit: e.target.value })}
            />
          </div>
        </div>

        <div>
          <label className="block text-sm mb-1">Protocole</label>
          <select
            className="w-full border rounded px-3 py-2 text-sm"
            value={form.protocol}
            onChange={(e) => setForm({ ...form, protocol: e.target.value as IoTProtocol })}
          >
            {PROTOCOLS.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
          <p className="text-xs text-gray-400 mt-1">
            Choisir "simulator" pour tester sans matériel, ou "mqtt" pour tester avec un broker MQTT en ligne.
          </p>
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <div className="flex justify-end gap-2 pt-2">
          <button type="button" onClick={onClose} className="px-4 py-2 text-sm rounded-md border">
            Annuler
          </button>
          <button
            type="submit"
            disabled={submitting}
            className="px-4 py-2 text-sm rounded-md bg-green-700 text-white hover:bg-green-800 disabled:opacity-50"
          >
            {submitting ? "Création..." : "Créer"}
          </button>
        </div>
      </form>
    </div>
  );
}
