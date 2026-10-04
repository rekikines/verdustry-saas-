"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  createSource,
  deleteSource,
  fetchSources,
  syncSource,
  type DataSource,
} from "@/features/sources/api";
import { fetchSites, type Site } from "@/features/sites/api";
import { getAccessToken } from "@/features/auth/storage";
import { extractDocument, ocrStatus } from "@/features/sources/ocr";
import {
  createDevice,
  type IoTCategory,
  type IoTProtocol,
  type IoTDeviceCreate,
} from "@/features/iot/api";

const CATEGORIES = [
  "Toutes",
  "Achats",
  "Énergie",
  "Eau",
  "Déchets",
  "Transport",
  "Stocks",
  "RH",
  "Auto",
];

const STATUS_STYLE: Record<string, string> = {
  ACTIVE: "bg-[#E8F7EE] text-[#0B6B3A]",
  FAILED: "bg-[#FBF1DF] text-[#C98A2C]",
  OCR_PENDING: "bg-[#EAF2F8] text-[#3D7AA8]",
  INACTIVE: "bg-[#F1F1EE] text-[#5A6F62]",
};

const STATUS_LABEL: Record<string, string> = {
  ACTIVE: "Active",
  FAILED: "Échec",
  OCR_PENDING: "OCR",
  INACTIVE: "Inactive",
};

const TYPE_LABEL: Record<string, string> = {
  DOCUMENT: "Document",
  ERP: "ERP",
  API: "API",
  IOT: "IoT",
  CSV: "CSV",
  SQL: "SQL",
  MANUAL: "Manuel",
};

const SOURCE_TYPES = [
  { type: "ERP", label: "ERP", desc: "Odoo, SAP, Sage, Oracle…", icon: "ERP" },
  { type: "SQL", label: "Base SQL", desc: "PostgreSQL, MySQL…", icon: "SQL" },
  { type: "API", label: "API externe", desc: "REST / fournisseurs", icon: "API" },
  {
    type: "CSV",
    label: "Fichier CSV / Excel",
    desc: "Import .csv, .xlsx, .xls",
    icon: "CSV",
  },
  { type: "IOT", label: "Capteur IoT", desc: "Compteur énergie, eau…", icon: "IoT" },
  {
    type: "DOCUMENT",
    label: "Document",
    desc: "PDF / image — OCR automatique",
    icon: "PDF",
  },
  {
    type: "MANUAL",
    label: "Saisie manuelle",
    desc: "Données manquantes",
    icon: "…/",
  },
] as const;

const IOT_DEVICE_TYPES = [
  { value: "energy_meter", label: "Compteur d'énergie électrique (kWh, puissance, cos φ)", unit: "kWh", category: "energie" as IoTCategory },
  { value: "energy_submeter", label: "Sous-comptage par machine", unit: "kWh", category: "energie" as IoTCategory },
  { value: "gas_meter", label: "Compteur gaz naturel", unit: "m3", category: "energie" as IoTCategory },
  { value: "fuel_level", label: "Niveau cuve fioul / carburant", unit: "%", category: "energie" as IoTCategory },
  { value: "solar_inverter", label: "Onduleur photovoltaïque (production solaire)", unit: "kWh", category: "energie" as IoTCategory },

  { value: "water_flow", label: "Débitmètre eau (débit / volume consommé)", unit: "m3", category: "eau" as IoTCategory },
  { value: "water_quality", label: "Sonde qualité eau (pH, turbidité, conductivité, O2 dissous)", unit: "pH", category: "eau" as IoTCategory },
  { value: "water_level", label: "Niveau bassin / cuve / STEP", unit: "%", category: "eau" as IoTCategory },
{ value: "waste_rfid", label: "Identification du flux (RFID/QR)", unit: "événement", category: "dechets" as IoTCategory },
  { value: "waste_level", label: "Niveau de remplissage bac / benne", unit: "%", category: "dechets" as IoTCategory },
  { value: "weight", label: "Bascule de pesée (poids collecté)", unit: "kg", category: "dechets" as IoTCategory },
  { value: "compactor_cycles", label: "Compacteur / presse (cycles hydrauliques)", unit: "cycles", category: "dechets" as IoTCategory },

  { value: "co2", label: "Capteur CO2 (NDIR)", unit: "ppm", category: "emissions" as IoTCategory },
  { value: "pm25", label: "Particules fines PM1 / PM2.5 / PM10", unit: "µg/m3", category: "emissions" as IoTCategory },
  { value: "voc", label: "COV (composés organiques volatils)", unit: "ppb", category: "emissions" as IoTCategory },
  { value: "stack_emissions", label: "Émissions cheminée (SO2, NOx, CO)", unit: "mg/Nm3", category: "emissions" as IoTCategory },
  { value: "opacity", label: "Opacité fumées cheminée", unit: "%", category: "emissions" as IoTCategory },

  { value: "temperature", label: "Température", unit: "°C", category: "ambiance" as IoTCategory },
  { value: "humidity", label: "Humidité", unit: "%", category: "ambiance" as IoTCategory },
  { value: "noise", label: "Bruit (sonomètre)", unit: "dB", category: "ambiance" as IoTCategory },
  { value: "vibration", label: "Vibration (maintenance prédictive)", unit: "mm/s", category: "ambiance" as IoTCategory },
];
const IOT_PROTOCOLS: { value: IoTProtocol; label: string }[] = [
  { value: "simulator", label: "Mode test (simulateur)" },
  { value: "modbus_tcp", label: "Modbus TCP" },
  { value: "modbus_rtu", label: "Modbus RTU (RS485)" },
  { value: "mqtt", label: "MQTT" },
  { value: "lorawan", label: "LoRaWAN" },
  { value: "http", label: "HTTP / REST" },
];

const IOT_CATEGORY_TO_TAB: Record<IoTCategory, string> = {
  energie: "Énergie",
  eau: "Eau",
  dechets: "Déchets",
  emissions: "Auto",
  ambiance: "Auto",
};

function formatSync(iso: string | null) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString("fr-FR", {
      day: "2-digit",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "—";
  }
}

export default function SourcesPage() {
  const router = useRouter();
  const [sources, setSources] = useState<DataSource[]>([]);
  const [sites, setSites] = useState<Site[]>([]);
  const [siteId, setSiteId] = useState("");
  const [filter, setFilter] = useState("Toutes");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [wizardOpen, setWizardOpen] = useState(false);
  const [ocrEngine, setOcrEngine] = useState("…");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [step, setStep] = useState(1);
  const [selectedType, setSelectedType] = useState<string | null>(null);
  const [wName, setWName] = useState("");
  const [wSiteId, setWSiteId] = useState("");
  const [wFile, setWFile] = useState<File | null>(null);

  const [saving, setSaving] = useState(false);
  const [wErpUrl, setWErpUrl] = useState("");
  const [wErpDb, setWErpDb] = useState("");
  const [wErpUsername, setWErpUsername] = useState("");
  const [wErpPassword, setWErpPassword] = useState("");
  const [wErpFrequency, setWErpFrequency] = useState("daily");
  const [wErpCategories, setWErpCategories] = useState<string[]>([]);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const ERP_CATEGORY_OPTIONS = CATEGORIES.filter((c) => c !== "Toutes");

  const [wApiCategory, setWApiCategory] = useState("Achats");
  const [wApiBaseUrl, setWApiBaseUrl] = useState("");
  const [wApiEndpointPath, setWApiEndpointPath] = useState("");
  const [wApiMethod, setWApiMethod] = useState<"GET" | "POST">("GET");
  const [wApiAuthType, setWApiAuthType] = useState<
    "none" | "api_key" | "bearer" | "basic"
  >("none");
  const [wApiKeyHeaderName, setWApiKeyHeaderName] = useState("X-API-Key");
  const [wApiKeyValue, setWApiKeyValue] = useState("");
  const [wApiBearerToken, setWApiBearerToken] = useState("");
  const [wApiBasicUsername, setWApiBasicUsername] = useState("");
  const [wApiBasicPassword, setWApiBasicPassword] = useState("");
  const [wApiResponseDataPath, setWApiResponseDataPath] = useState("");
  const [wApiFrequency, setWApiFrequency] = useState("daily");
  const [wApiFieldMap, setWApiFieldMap] = useState<
    { source: string; target: string }[]
  >([{ source: "", target: "" }]);

  function updateApiFieldMap(
    index: number,
    key: "source" | "target",
    value: string
  ) {
    setWApiFieldMap((prev) =>
      prev.map((row, i) => (i === index ? { ...row, [key]: value } : row))
    );
  }
  function addApiFieldMapRow() {
    setWApiFieldMap((prev) => [...prev, { source: "", target: "" }]);
  }
  function removeApiFieldMapRow(index: number) {
    setWApiFieldMap((prev) => prev.filter((_, i) => i !== index));
  }

  const [wIotDeviceUid, setWIotDeviceUid] = useState("");
  const [wIotDeviceType, setWIotDeviceType] = useState(IOT_DEVICE_TYPES[0].value);
  const [wIotProtocol, setWIotProtocol] = useState<IoTProtocol>("simulator");
  const [wIotUnit, setWIotUnit] = useState(IOT_DEVICE_TYPES[0].unit);
  const [wIotMin, setWIotMin] = useState("");
  const [wIotMax, setWIotMax] = useState("");
  const [wIotThreshold, setWIotThreshold] = useState("");
  const [wIotHost, setWIotHost] = useState("");
  const [wIotPort, setWIotPort] = useState("");
  const [wIotMqttTopic, setWIotMqttTopic] = useState("");

  const iotDeviceTypeInfo =
    IOT_DEVICE_TYPES.find((d) => d.value === wIotDeviceType) ?? IOT_DEVICE_TYPES[0];
  const iotNeedsConnectionParams =
    wIotProtocol === "modbus_tcp" || wIotProtocol === "modbus_rtu" || wIotProtocol === "mqtt";

  function toggleErpCategory(cat: string) {
    setWErpCategories((prev) =>
      prev.includes(cat) ? prev.filter((c) => c !== cat) : [...prev, cat]
    );
  }

  function onIotDeviceTypeChange(value: string) {
    setWIotDeviceType(value);
    const info = IOT_DEVICE_TYPES.find((d) => d.value === value);
    if (info) setWIotUnit(info.unit);
  }

  const load = useCallback(async () => {
    if (!getAccessToken()) {
      router.push("/login");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const [sList, siteList] = await Promise.all([
        fetchSources(siteId || undefined),
        fetchSites(),
      ]);
      setSources(sList);
      setSites(siteList);
      if (!siteId && siteList[0]) setSiteId(siteList[0].id);
      if (!wSiteId && siteList[0]) setWSiteId(siteList[0].id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur chargement");
    } finally {
      setLoading(false);
    }
  }, [router, siteId, wSiteId]);

  useEffect(() => {
    load();
    ocrStatus()
      .then((s) => setOcrEngine(s.engine))
      .catch(() => setOcrEngine("simulation"));
  }, [load]);

  useEffect(() => {
    if (!wFile) {
      setPreviewUrl(null);
      return;
    }
    const url = URL.createObjectURL(wFile);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [wFile]);

  const filtered = useMemo(
    () =>
      filter === "Toutes"
        ? sources
        : sources.filter((s) => s.category === filter),
    [sources, filter]
  );

  function openWizard() {
    setStep(1);
    setSelectedType(null);
    setWName("");
    setWFile(null);
    setPreviewUrl(null);
    setWErpUrl("");
    setWErpDb("");
    setWErpUsername("");
    setWErpPassword("");
    setWErpFrequency("daily");
    setWErpCategories([]);
    setWSiteId(siteId || sites[0]?.id || "");

    setWApiCategory("Achats");
    setWApiBaseUrl("");
    setWApiEndpointPath("");
    setWApiMethod("GET");
    setWApiAuthType("none");
    setWApiKeyHeaderName("X-API-Key");
    setWApiKeyValue("");
    setWApiBearerToken("");
    setWApiBasicUsername("");
    setWApiBasicPassword("");
    setWApiResponseDataPath("");
    setWApiFrequency("daily");
    setWApiFieldMap([{ source: "", target: "" }]);

    setWIotDeviceUid("");
    setWIotDeviceType(IOT_DEVICE_TYPES[0].value);
    setWIotProtocol("simulator");
    setWIotUnit(IOT_DEVICE_TYPES[0].unit);
    setWIotMin("");
    setWIotMax("");
    setWIotThreshold("");
    setWIotHost("");
    setWIotPort("");
    setWIotMqttTopic("");

    setWizardOpen(true);
  }

  async function submitWizard() {
    if (!selectedType || !wSiteId) return;
    if (selectedType !== "DOCUMENT" && !wName.trim()) return;
    if (selectedType === "DOCUMENT" && !wFile) return;

    setSaving(true);
    setError("");
    try {
      if (selectedType === "DOCUMENT" && wFile) {
        await extractDocument({ file: wFile, siteId: wSiteId });
      } else if (selectedType === "ERP") {
        await createSource({
          name: wName.trim(),
          type: "ERP",
          category: wErpCategories[0] || "Achats",
          site_id: wSiteId,
          config: {
            erp_type: "odoo",
            url: wErpUrl.trim(),
            db_name: wErpDb.trim(),
            username: wErpUsername.trim(),
            password: wErpPassword,
            sync_frequency: wErpFrequency,
            categories: wErpCategories,
          },
        });
      } else if (selectedType === "API") {
        const credentials =
          wApiAuthType === "api_key"
            ? { header_name: wApiKeyHeaderName.trim(), api_key: wApiKeyValue }
            : wApiAuthType === "bearer"
            ? { token: wApiBearerToken }
            : wApiAuthType === "basic"
            ? { username: wApiBasicUsername.trim(), password: wApiBasicPassword }
            : undefined;

        const field_map: Record<string, string> = {};
        wApiFieldMap.forEach((row) => {
          if (row.source.trim() && row.target.trim()) {
            field_map[row.source.trim()] = row.target.trim();
          }
        });

        await createSource({
          name: wName.trim(),
          type: "API",
          category: wApiCategory,
          site_id: wSiteId,
          config: {
            base_url: wApiBaseUrl.trim(),
            endpoint_path: wApiEndpointPath.trim(),
            http_method: wApiMethod,
            auth_type: wApiAuthType,
            credentials,
            response_data_path: wApiResponseDataPath.trim(),
            pagination_type: "none",
            field_map,
            sync_frequency: wApiFrequency,
          },
        });
      } else if (selectedType === "IOT") {
        const source = await createSource({
          name: wName.trim(),
          type: "IOT",
          category: IOT_CATEGORY_TO_TAB[iotDeviceTypeInfo.category] || "Auto",
          site_id: wSiteId,
          config: {
            protocol: wIotProtocol,
            device_type: wIotDeviceType,
          },
        });

        const connection_params: Record<string, unknown> = {};
        if (iotNeedsConnectionParams) {
          if (wIotHost.trim()) connection_params.host = wIotHost.trim();
          if (wIotPort.trim()) connection_params.port = Number(wIotPort);
          if (wIotProtocol === "mqtt" && wIotMqttTopic.trim()) {
            connection_params.topic = wIotMqttTopic.trim();
          }
        }

        const payload: IoTDeviceCreate = {
          site_id: wSiteId,
          data_source_id: source.id,
          device_uid: wIotDeviceUid.trim(),
          name: wName.trim(),
          device_type: wIotDeviceType,
          category: iotDeviceTypeInfo.category,
          protocol: wIotProtocol,
          unit: wIotUnit.trim(),
          connection_params,
          min_valid_value: wIotMin.trim() ? Number(wIotMin) : null,
          max_valid_value: wIotMax.trim() ? Number(wIotMax) : null,
          alert_threshold: wIotThreshold.trim() ? Number(wIotThreshold) : null,
        };
        await createDevice(payload);
      } else {
        await createSource({
          name: wName.trim(),
          type: selectedType,
          category: "Auto",
          site_id: wSiteId,
          config: {},
        });
      }
      setWizardOpen(false);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Création impossible");
    } finally {
      setSaving(false);
    }
  }

  async function onSync(id: string) {
    try {
      await syncSource(id);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Sync échouée");
    }
  }

  async function onDelete(id: string) {
    if (!confirm("Supprimer cette source ?")) return;
    try {
      await deleteSource(id);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Suppression échouée");
    }
  }

  function toggleSelect(id: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleSelectAll() {
    if (selectedIds.size === filtered.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(filtered.map((s) => s.id)));
    }
  }

  async function onBulkDelete() {
    if (selectedIds.size === 0) return;
    if (!confirm(`Supprimer ${selectedIds.size} source(s) sélectionnée(s) ?`)) return;
    setError("");
    try {
      await Promise.all(Array.from(selectedIds).map((id) => deleteSource(id)));
      setSelectedIds(new Set());
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Suppression par lot échouée");
    }
  }

  useEffect(() => {
    setSelectedIds(new Set());
  }, [filter]);

  const canContinueStep1 = !!selectedType;
  const canContinueStep2 =
    selectedType === "DOCUMENT"
      ? !!wFile && !!wSiteId
      : selectedType === "ERP"
      ? !!wName.trim() && !!wSiteId && !!wErpUrl.trim() && !!wErpDb.trim() &&
        !!wErpUsername.trim() && !!wErpPassword && wErpCategories.length > 0
      : selectedType === "IOT"
      ? !!wName.trim() &&
        !!wSiteId &&
        !!wIotDeviceUid.trim() &&
        !!wIotUnit.trim() &&
        (!iotNeedsConnectionParams || (!!wIotHost.trim() && !!wIotPort.trim()))
      : selectedType === "API"
      ? !!wName.trim() && !!wSiteId && !!wApiBaseUrl.trim()
      : !!wName.trim() && !!wSiteId;

  return (
    <>
      <header className="flex items-center justify-between border-b border-[#DCE8E0] bg-white px-7 py-3.5">
        <div>
          <h1 className="text-[18px] font-bold text-[#1A2E22]">
            Sources de données
          </h1>
          <p className="mt-0.5 text-[12.5px] text-[#5A6F62]">
            Collecte multi-sources · OCR {ocrEngine}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={siteId}
            onChange={(e) => setSiteId(e.target.value)}
            className="rounded-lg border border-[#DCE8E0] bg-white px-3.5 py-2 text-[13px] outline-none focus:border-[#00A651]"
          >
            {sites.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={openWizard}
            className="rounded-lg bg-[#00A651] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#008F45]"
          >
            + Ajouter une source
          </button>
        </div>
      </header>

      <div className="flex-1 overflow-y-auto p-6">
        {error && (
          <div className="mb-4 rounded-lg bg-[#FBEAE7] px-3 py-2 text-sm text-[#B5473A]">
            {error}
          </div>
        )}

        <div className="mb-4 flex flex-wrap gap-2">
          {CATEGORIES.map((c) => (
            <button
              key={c}
              type="button"
              onClick={() => setFilter(c)}
              className={`rounded-full border px-3.5 py-1.5 text-xs font-medium transition ${
                filter === c
                  ? "border-[#00A651] bg-[#00A651] text-white"
                  : "border-[#DCE8E0] bg-white text-[#5A6F62] hover:border-[#7BC99A]"
              }`}
            >
              {c}
            </button>
          ))}
        </div>
        {selectedIds.size > 0 && (
          <div className="mb-3 flex items-center justify-between rounded-lg bg-[#E8F7EE] px-4 py-2.5">
            <span className="text-sm font-medium text-[#0B6B3A]">
              {selectedIds.size} source(s) sélectionnée(s)
            </span>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={onBulkDelete}
                className="rounded-lg bg-[#B5473A] px-3.5 py-1.5 text-xs font-semibold text-white hover:bg-[#9C3B30]"
              >
                Supprimer la sélection
              </button>
              <button
                type="button"
                onClick={() => setSelectedIds(new Set())}
                className="rounded-lg border border-[#DCE8E0] bg-white px-3.5 py-1.5 text-xs font-medium text-[#1A2E22] hover:bg-[#F7FAF8]"
              >
                Annuler
              </button>
            </div>
          </div>
        )}

        <div className="overflow-hidden rounded-xl border border-[#DCE8E0] bg-white">
          <table className="w-full border-collapse text-left">
            <thead>
              <tr className="bg-[#E8F7EE] text-[11.5px] font-semibold uppercase tracking-wide text-[#5A6F62]">
                <th className="w-10 px-3.5 py-2.5">
                  <input
                    type="checkbox"
                    checked={filtered.length > 0 && selectedIds.size === filtered.length}
                    onChange={toggleSelectAll}
                  />
                </th>
                <th className="px-3.5 py-2.5">Catégorie</th>
                <th className="px-3.5 py-2.5">Type</th>
                <th className="px-3.5 py-2.5">Source</th>
                <th className="px-3.5 py-2.5">Dernière sync</th>
                <th className="px-3.5 py-2.5">Volume</th>
                <th className="px-3.5 py-2.5">Statut</th>
                <th className="px-3.5 py-2.5" />
              </tr>
            </thead>

            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={8} className="px-3.5 py-10 text-center text-sm text-[#5A6F62]">
                    Chargement…
                  </td>
                </tr>
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-3.5 py-10 text-center text-sm text-[#5A6F62]">
                    Aucune source. Utilisez « Ajouter une source ».
                  </td>
                </tr>
              ) : (
                filtered.map((s) => (
                  <tr
                    key={s.id}
                    className="border-t border-[#DCE8E0] text-[13.5px] hover:bg-[#FAFBF9]"
                  >
                    <td className="px-3.5 py-3">
                      <input
                        type="checkbox"
                        checked={selectedIds.has(s.id)}
                        onChange={() => toggleSelect(s.id)}
                      />
                    </td>
                    <td className="px-3.5 py-3">
                      <span className="rounded-md bg-[#EEF3EF] px-2.5 py-1 text-xs font-semibold text-[#3D8B5F]">
                        {s.category}
                      </span>
                    </td>
                    <td className="px-3.5 py-3">{TYPE_LABEL[s.type] || s.type}</td>
                    <td className="px-3.5 py-3 font-medium">{s.name}</td>
                    <td className="px-3.5 py-3 text-[#5A6F62]">
                      {formatSync(s.last_sync_at)}
                    </td>
                    <td className="px-3.5 py-3 text-[#5A6F62]">{s.volume ?? "—"}</td>
                    <td className="px-3.5 py-3">
                      <span
                        className={`inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-semibold ${
                          STATUS_STYLE[s.status] || STATUS_STYLE.INACTIVE
                        }`}
                      >
                        <span className="h-1.5 w-1.5 rounded-full bg-current" />
                        {STATUS_LABEL[s.status] || s.status}
                      </span>
                    </td>
                    <td className="px-3.5 py-3">
                      <div className="flex justify-end gap-2">
                        {["ERP", "API", "IOT", "SQL"].includes(s.type) && (
                          <button
                            type="button"
                            onClick={() => onSync(s.id)}
                            className="rounded-md border border-[#DCE8E0] px-2.5 py-1 text-xs font-medium hover:bg-[#E8F7EE]"
                          >
                            Sync
                          </button>
                        )}
                        <button
                          type="button"
                          onClick={() => onDelete(s.id)}
                          className="rounded-md border border-[#DCE8E0] px-2.5 py-1 text-xs text-[#B5473A] hover:bg-[#FBEAE7]"
                        >
                          Suppr.
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {wizardOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-[rgba(23,60,46,0.45)] p-4">
          <div className="max-h-[90vh] w-full max-w-[540px] overflow-y-auto rounded-2xl bg-white shadow-2xl">
            <div className="border-b border-[#E8EEE9] px-6 pb-4 pt-6">
              <h3 className="text-lg font-bold text-[#1A2E22]">
                Ajouter une source de données
              </h3>
              <p className="mt-1 text-[13px] text-[#5A6F62]">
                L&apos;extraction et le mapping sont automatiques
              </p>
              <div className="mt-5 flex gap-6 text-[12px] font-semibold">
                {[
                  { n: 1, label: "Type de source" },
                  { n: 2, label: "Configuration" },
                  { n: 3, label: "Activation" },
                ].map((s) => (
                  <div
                    key={s.n}
                    className={`flex items-center gap-2 border-b-2 pb-2 ${
                      step === s.n
                        ? "border-[#00A651] text-[#00A651]"
                        : "border-transparent text-[#9AAB9F]"
                    }`}
                  >
                    <span
                      className={`flex h-5 w-5 items-center justify-center rounded-full text-[10px] ${
                        step === s.n
                          ? "bg-[#00A651] text-white"
                          : "bg-[#F0F2F1] text-[#9AAB9F]"
                      }`}
                    >
                      {s.n}
                    </span>
                    {s.label}
                  </div>
                ))}
              </div>
            </div>

            <div className="px-6 py-5">
              {step === 1 && (
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                  {SOURCE_TYPES.map((t) => (
                    <button
                      key={t.type + t.label}
                      type="button"
                      onClick={() => setSelectedType(t.type)}
                      className={`rounded-xl border p-4 text-left transition ${
                        selectedType === t.type
                          ? "border-[#00A651] bg-[#E8F7EE] shadow-sm"
                          : "border-[#E8EEE9] hover:border-[#7BC99A]"
                      }`}
                    >
                      <div className="mb-2 flex h-9 w-9 items-center justify-center rounded-lg bg-[#E8F7EE] text-[10px] font-bold text-[#0B6B3A]">
                        {t.icon}
                      </div>
                      <div className="text-[13px] font-bold text-[#1A2E22]">
                        {t.label}
                      </div>
                      <div className="mt-0.5 text-[11px] text-[#5A6F62]">
                        {t.desc}
                      </div>
                    </button>
                  ))}
                </div>
              )}

              {step === 2 && selectedType === "DOCUMENT" && (
                <div className="space-y-4">
                  <div>
                    <label className="mb-1.5 block text-xs font-semibold uppercase text-[#5A6F62]">
                      Site
                    </label>
                    <select
                      value={wSiteId}
                      onChange={(e) => setWSiteId(e.target.value)}
                      className="w-full rounded-xl border border-[#E8EEE9] px-3.5 py-3 text-sm outline-none focus:border-[#00A651]"
                    >
                      {sites.map((s) => (
                        <option key={s.id} value={s.id}>
                          {s.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="mb-1.5 block text-xs font-semibold uppercase text-[#5A6F62]">
                      Fichier (PDF ou image)
                    </label>
                    <label className="flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed border-[#DCE8E0] bg-[#F7FAF8] px-4 py-6 transition hover:border-[#00A651] hover:bg-[#E8F7EE]/40">
                      <span className="text-sm font-semibold text-[#0B6B3A]">
                        {wFile ? wFile.name : "Choisir un fichier"}
                      </span>
                      <span className="mt-1 text-[12px] text-[#5A6F62]">
                        Type & catégorie détectés automatiquement
                      </span>
                      <input
                        type="file"
                        accept=".pdf,image/*"
                        className="hidden"
                        onChange={(e) => setWFile(e.target.files?.[0] ?? null)}
                      />
                    </label>
                  </div>

                  {previewUrl && wFile && (
                    <div className="overflow-hidden rounded-xl border border-[#DCE8E0] bg-[#F7FAF8]">
                      <div className="border-b border-[#E8EEE9] px-3 py-2 text-[11px] font-semibold uppercase tracking-wide text-[#5A6F62]">
                        Aperçu
                      </div>
                      <div className="flex max-h-[220px] items-center justify-center p-3">
                        {wFile.type.startsWith("image/") ? (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img
                            src={previewUrl}
                            alt="Aperçu du document"
                            className="max-h-[200px] max-w-full rounded-lg object-contain shadow-sm"
                          />
                        ) : wFile.type === "application/pdf" ? (
                          <div className="flex flex-col items-center gap-2 py-6 text-center">
                            <span className="rounded-lg bg-[#E8F7EE] px-3 py-1.5 text-xs font-bold text-[#0B6B3A]">
                              PDF
                            </span>
                            <span className="max-w-[240px] truncate text-[13px] text-[#1A2E22]">
                              {wFile.name}
                            </span>
                            <span className="text-[11px] text-[#5A6F62]">
                              Aperçu image non disponible pour les PDF
                            </span>
                          </div>
                        ) : (
                          <span className="text-sm text-[#5A6F62]">{wFile.name}</span>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {step === 2 &&
                selectedType &&
                selectedType !== "DOCUMENT" &&
                selectedType !== "ERP" &&
                selectedType !== "IOT" &&
                selectedType !== "API" && (
                  <div className="space-y-4">
                    <div>
                      <label className="mb-1.5 block text-xs font-semibold uppercase text-[#5A6F62]">
                        Nom de la source
                      </label>
                      <input
                        value={wName}
                        onChange={(e) => setWName(e.target.value)}
                        placeholder="ex. Odoo Production"
                        className="w-full rounded-xl border border-[#E8EEE9] px-3.5 py-3 text-sm outline-none focus:border-[#00A651]"
                      />
                    </div>
                    <div>
                      <label className="mb-1.5 block text-xs font-semibold uppercase text-[#5A6F62]">
                        Site
                      </label>
                      <select
                        value={wSiteId}
                        onChange={(e) => setWSiteId(e.target.value)}
                        className="w-full rounded-xl border border-[#E8EEE9] px-3.5 py-3 text-sm outline-none focus:border-[#00A651]"
                      >
                        {sites.map((s) => (
                          <option key={s.id} value={s.id}>
                            {s.name}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                )}

              {step === 2 && selectedType === "ERP" && (
                <div className="space-y-4">
                  <div>
                    <label className="mb-1.5 block text-xs font-semibold uppercase text-[#5A6F62]">
                      Nom de la connexion
                    </label>
                    <input
                      value={wName}
                      onChange={(e) => setWName(e.target.value)}
                      placeholder="ex. Odoo Production"
                      className="w-full rounded-xl border border-[#E8EEE9] px-3.5 py-3 text-sm outline-none focus:border-[#00A651]"
                    />
                  </div>

                  <div>
                    <label className="mb-1.5 block text-xs font-semibold uppercase text-[#5A6F62]">
                      Site
                    </label>
                    <select
                      value={wSiteId}
                      onChange={(e) => setWSiteId(e.target.value)}
                      className="w-full rounded-xl border border-[#E8EEE9] px-3.5 py-3 text-sm outline-none focus:border-[#00A651]"
                    >
                      {sites.map((s) => (
                        <option key={s.id} value={s.id}>{s.name}</option>
                      ))}
                    </select>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="mb-1.5 block text-xs font-semibold uppercase text-[#5A6F62]">
                        URL Odoo
                      </label>
                      <input
                        value={wErpUrl}
                        onChange={(e) => setWErpUrl(e.target.value)}
                        placeholder="http://localhost:8069"
                        className="w-full rounded-xl border border-[#E8EEE9] px-3.5 py-3 text-sm outline-none focus:border-[#00A651]"
                      />
                    </div>
                    <div>
                      <label className="mb-1.5 block text-xs font-semibold uppercase text-[#5A6F62]">
                        Base de données
                      </label>
                      <input
                        value={wErpDb}
                        onChange={(e) => setWErpDb(e.target.value)}
                        placeholder="test"
                        className="w-full rounded-xl border border-[#E8EEE9] px-3.5 py-3 text-sm outline-none focus:border-[#00A651]"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="mb-1.5 block text-xs font-semibold uppercase text-[#5A6F62]">
                        Utilisateur
                      </label>
                      <input
                        value={wErpUsername}
                        onChange={(e) => setWErpUsername(e.target.value)}
                        placeholder="admin@test.com"
                        className="w-full rounded-xl border border-[#E8EEE9] px-3.5 py-3 text-sm outline-none focus:border-[#00A651]"
                      />
                    </div>
                    <div>
                      <label className="mb-1.5 block text-xs font-semibold uppercase text-[#5A6F62]">
                        Mot de passe
                      </label>
                      <input
                        type="password"
                        value={wErpPassword}
                        onChange={(e) => setWErpPassword(e.target.value)}
                        placeholder="••••••••"
                        className="w-full rounded-xl border border-[#E8EEE9] px-3.5 py-3 text-sm outline-none focus:border-[#00A651]"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="mb-1.5 block text-xs font-semibold uppercase text-[#5A6F62]">
                      Fréquence de synchronisation
                    </label>
                    <select
                      value={wErpFrequency}
                      onChange={(e) => setWErpFrequency(e.target.value)}
                      className="w-full rounded-xl border border-[#E8EEE9] px-3.5 py-3 text-sm outline-none focus:border-[#00A651]"
                    >
                      <option value="manual">Manuelle</option>
                      <option value="hourly">Toutes les heures</option>
                      <option value="daily">Quotidienne</option>
                      <option value="realtime">Temps réel</option>
                    </select>
                  </div>

                  <div>
                    <label className="mb-1.5 block text-xs font-semibold uppercase text-[#5A6F62]">
                      Catégories à synchroniser
                    </label>
                    <div className="flex flex-wrap gap-2">
                      {ERP_CATEGORY_OPTIONS.map((cat) => (
                        <button
                          key={cat}
                          type="button"
                          onClick={() => toggleErpCategory(cat)}
                          className={`rounded-full border px-3 py-1.5 text-xs font-medium transition ${
                            wErpCategories.includes(cat)
                              ? "border-[#00A651] bg-[#00A651] text-white"
                              : "border-[#DCE8E0] bg-white text-[#5A6F62] hover:border-[#7BC99A]"
                          }`}
                        >
                          {cat}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {step === 2 && selectedType === "IOT" && (
                <div className="space-y-4">
                  <div>
                    <label className="mb-1.5 block text-xs font-semibold uppercase text-[#5A6F62]">
                      Nom du capteur
                    </label>
                    <input
                      value={wName}
                      onChange={(e) => setWName(e.target.value)}
                      placeholder="ex. Compteur électrique Atelier 2"
                      className="w-full rounded-xl border border-[#E8EEE9] px-3.5 py-3 text-sm outline-none focus:border-[#00A651]"
                    />
                  </div>

                  <div>
                    <label className="mb-1.5 block text-xs font-semibold uppercase text-[#5A6F62]">
                      Site
                    </label>
                    <select
                      value={wSiteId}
                      onChange={(e) => setWSiteId(e.target.value)}
                      className="w-full rounded-xl border border-[#E8EEE9] px-3.5 py-3 text-sm outline-none focus:border-[#00A651]"
                    >
                      {sites.map((s) => (
                        <option key={s.id} value={s.id}>{s.name}</option>
                      ))}
                    </select>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="mb-1.5 block text-xs font-semibold uppercase text-[#5A6F62]">
                        Type de capteur
                      </label>
                      <select
                        value={wIotDeviceType}
                        onChange={(e) => onIotDeviceTypeChange(e.target.value)}
                        className="w-full rounded-xl border border-[#E8EEE9] px-3.5 py-3 text-sm outline-none focus:border-[#00A651]"
                      >
                        {IOT_DEVICE_TYPES.map((d) => (
                          <option key={d.value} value={d.value}>{d.label}</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="mb-1.5 block text-xs font-semibold uppercase text-[#5A6F62]">
                        Unité
                      </label>
                      <input
                        value={wIotUnit}
                        onChange={(e) => setWIotUnit(e.target.value)}
                        placeholder="kWh, m3, ppm..."
                        className="w-full rounded-xl border border-[#E8EEE9] px-3.5 py-3 text-sm outline-none focus:border-[#00A651]"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="mb-1.5 block text-xs font-semibold uppercase text-[#5A6F62]">
                      Identifiant matériel (device UID)
                    </label>
                    <input
                      value={wIotDeviceUid}
                      onChange={(e) => setWIotDeviceUid(e.target.value)}
                      placeholder="ex. sim-energy-01, DevEUI, n° série..."
                      className="w-full rounded-xl border border-[#E8EEE9] px-3.5 py-3 text-sm outline-none focus:border-[#00A651]"
                    />
                  </div>

                  <div>
                    <label className="mb-1.5 block text-xs font-semibold uppercase text-[#5A6F62]">
                      Protocole
                    </label>
                    <select
                      value={wIotProtocol}
                      onChange={(e) => setWIotProtocol(e.target.value as IoTProtocol)}
                      className="w-full rounded-xl border border-[#E8EEE9] px-3.5 py-3 text-sm outline-none focus:border-[#00A651]"
                    >
                      {IOT_PROTOCOLS.map((p) => (
                        <option key={p.value} value={p.value}>{p.label}</option>
                      ))}
                    </select>
                    {wIotProtocol === "simulator" && (
                      <p className="mt-1.5 text-[11.5px] text-[#3D8B5F]">
                        Génère automatiquement des valeurs de test réalistes toutes les 10s — idéal pour valider le pipeline avant de brancher un vrai capteur.
                      </p>
                    )}
                  </div>

                  {iotNeedsConnectionParams && (
                    <div className="space-y-3 rounded-xl border border-dashed border-[#DCE8E0] p-3.5">
                      <p className="text-[11px] font-semibold uppercase tracking-wide text-[#5A6F62]">
                        Paramètres de connexion
                      </p>
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label className="mb-1.5 block text-xs text-[#5A6F62]">
                            {wIotProtocol === "mqtt" ? "Broker" : "Adresse IP / hôte"}
                          </label>
                          <input
                            value={wIotHost}
                            onChange={(e) => setWIotHost(e.target.value)}
                            placeholder="192.168.1.50"
                            className="w-full rounded-xl border border-[#E8EEE9] px-3.5 py-2.5 text-sm outline-none focus:border-[#00A651]"
                          />
                        </div>
                        <div>
                          <label className="mb-1.5 block text-xs text-[#5A6F62]">Port</label>
                          <input
                            value={wIotPort}
                            onChange={(e) => setWIotPort(e.target.value)}
                            placeholder={wIotProtocol === "mqtt" ? "1883" : "502"}
                            className="w-full rounded-xl border border-[#E8EEE9] px-3.5 py-2.5 text-sm outline-none focus:border-[#00A651]"
                          />
                        </div>
                      </div>
                      {wIotProtocol === "mqtt" && (
                        <div>
                          <label className="mb-1.5 block text-xs text-[#5A6F62]">Topic</label>
                          <input
                            value={wIotMqttTopic}
                            onChange={(e) => setWIotMqttTopic(e.target.value)}
                            placeholder="verdustry/sim-energy-01/reading"
                            className="w-full rounded-xl border border-[#E8EEE9] px-3.5 py-2.5 text-sm outline-none focus:border-[#00A651]"
                          />
                        </div>
                      )}
                    </div>
                  )}

                  <div className="grid grid-cols-3 gap-3">
                    <div>
                      <label className="mb-1.5 block text-xs font-semibold uppercase text-[#5A6F62]">
                        Min valide
                      </label>
                      <input
                        value={wIotMin}
                        onChange={(e) => setWIotMin(e.target.value)}
                        placeholder="optionnel"
                        className="w-full rounded-xl border border-[#E8EEE9] px-3.5 py-2.5 text-sm outline-none focus:border-[#00A651]"
                      />
                    </div>
                    <div>
                      <label className="mb-1.5 block text-xs font-semibold uppercase text-[#5A6F62]">
                        Max valide
                      </label>
                      <input
                        value={wIotMax}
                        onChange={(e) => setWIotMax(e.target.value)}
                        placeholder="optionnel"
                        className="w-full rounded-xl border border-[#E8EEE9] px-3.5 py-2.5 text-sm outline-none focus:border-[#00A651]"
                      />
                    </div>
                    <div>
                      <label className="mb-1.5 block text-xs font-semibold uppercase text-[#5A6F62]">
                        Seuil d&apos;alerte
                      </label>
                      <input
                        value={wIotThreshold}
                        onChange={(e) => setWIotThreshold(e.target.value)}
                        placeholder="optionnel"
                        className="w-full rounded-xl border border-[#E8EEE9] px-3.5 py-2.5 text-sm outline-none focus:border-[#00A651]"
                      />
                    </div>
                  </div>
                </div>
              )}

              {step === 2 && selectedType === "API" && (
                <div className="space-y-4">
                  <div>
                    <label className="mb-1.5 block text-xs font-semibold uppercase text-[#5A6F62]">
                      Nom de la source
                    </label>
                    <input
                      value={wName}
                      onChange={(e) => setWName(e.target.value)}
                      placeholder="ex. API Fournisseur Energie"
                      className="w-full rounded-xl border border-[#E8EEE9] px-3.5 py-3 text-sm outline-none focus:border-[#00A651]"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="mb-1.5 block text-xs font-semibold uppercase text-[#5A6F62]">
                        Site
                      </label>
                      <select
                        value={wSiteId}
                        onChange={(e) => setWSiteId(e.target.value)}
                        className="w-full rounded-xl border border-[#E8EEE9] px-3.5 py-3 text-sm outline-none focus:border-[#00A651]"
                      >
                        {sites.map((s) => (
                          <option key={s.id} value={s.id}>{s.name}</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="mb-1.5 block text-xs font-semibold uppercase text-[#5A6F62]">
                        Catégorie
                      </label>
                      <select
                        value={wApiCategory}
                        onChange={(e) => setWApiCategory(e.target.value)}
                        className="w-full rounded-xl border border-[#E8EEE9] px-3.5 py-3 text-sm outline-none focus:border-[#00A651]"
                      >
                        {ERP_CATEGORY_OPTIONS.map((cat) => (
                          <option key={cat} value={cat}>{cat}</option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-3">
                    <div className="col-span-2">
                      <label className="mb-1.5 block text-xs font-semibold uppercase text-[#5A6F62]">
                        URL de base
                      </label>
                      <input
                        value={wApiBaseUrl}
                        onChange={(e) => setWApiBaseUrl(e.target.value)}
                        placeholder="https://api.fournisseur.com"
                        className="w-full rounded-xl border border-[#E8EEE9] px-3.5 py-3 text-sm outline-none focus:border-[#00A651]"
                      />
                    </div>
                    <div>
                      <label className="mb-1.5 block text-xs font-semibold uppercase text-[#5A6F62]">
                        Méthode
                      </label>
                      <select
                        value={wApiMethod}
                        onChange={(e) => setWApiMethod(e.target.value as "GET" | "POST")}
                        className="w-full rounded-xl border border-[#E8EEE9] px-3.5 py-3 text-sm outline-none focus:border-[#00A651]"
                      >
                        <option value="GET">GET</option>
                        <option value="POST">POST</option>
                      </select>
                    </div>
                  </div>

                  <div>
                    <label className="mb-1.5 block text-xs font-semibold uppercase text-[#5A6F62]">
                      Chemin de l&apos;endpoint
                    </label>
                    <input
                      value={wApiEndpointPath}
                      onChange={(e) => setWApiEndpointPath(e.target.value)}
                      placeholder="v1/invoices"
                      className="w-full rounded-xl border border-[#E8EEE9] px-3.5 py-3 text-sm outline-none focus:border-[#00A651]"
                    />
                  </div>

                  <div>
                    <label className="mb-1.5 block text-xs font-semibold uppercase text-[#5A6F62]">
                      Authentification
                    </label>
                    <select
                      value={wApiAuthType}
                      onChange={(e) =>
                        setWApiAuthType(e.target.value as typeof wApiAuthType)
                      }
                      className="w-full rounded-xl border border-[#E8EEE9] px-3.5 py-3 text-sm outline-none focus:border-[#00A651]"
                    >
                      <option value="none">Aucune</option>
                      <option value="api_key">Clé API (header)</option>
                      <option value="bearer">Bearer token</option>
                      <option value="basic">Basic (utilisateur / mot de passe)</option>
                    </select>
                  </div>

                  {wApiAuthType === "api_key" && (
                    <div className="grid grid-cols-2 gap-3 rounded-xl border border-dashed border-[#DCE8E0] p-3.5">
                      <div>
                        <label className="mb-1.5 block text-xs text-[#5A6F62]">
                          Nom du header
                        </label>
                        <input
                          value={wApiKeyHeaderName}
                          onChange={(e) => setWApiKeyHeaderName(e.target.value)}
                          placeholder="X-API-Key"
                          className="w-full rounded-xl border border-[#E8EEE9] px-3.5 py-2.5 text-sm outline-none focus:border-[#00A651]"
                        />
                      </div>
                      <div>
                        <label className="mb-1.5 block text-xs text-[#5A6F62]">
                          Clé
                        </label>
                        <input
                          type="password"
                          value={wApiKeyValue}
                          onChange={(e) => setWApiKeyValue(e.target.value)}
                          placeholder="••••••••"
                          className="w-full rounded-xl border border-[#E8EEE9] px-3.5 py-2.5 text-sm outline-none focus:border-[#00A651]"
                        />
                      </div>
                    </div>
                  )}

                  {wApiAuthType === "bearer" && (
                    <div className="rounded-xl border border-dashed border-[#DCE8E0] p-3.5">
                      <label className="mb-1.5 block text-xs text-[#5A6F62]">
                        Token
                      </label>
                      <input
                        type="password"
                        value={wApiBearerToken}
                        onChange={(e) => setWApiBearerToken(e.target.value)}
                        placeholder="••••••••"
                        className="w-full rounded-xl border border-[#E8EEE9] px-3.5 py-2.5 text-sm outline-none focus:border-[#00A651]"
                      />
                    </div>
                  )}

                  {wApiAuthType === "basic" && (
                    <div className="grid grid-cols-2 gap-3 rounded-xl border border-dashed border-[#DCE8E0] p-3.5">
                      <div>
                        <label className="mb-1.5 block text-xs text-[#5A6F62]">
                          Utilisateur
                        </label>
                        <input
                          value={wApiBasicUsername}
                          onChange={(e) => setWApiBasicUsername(e.target.value)}
                          className="w-full rounded-xl border border-[#E8EEE9] px-3.5 py-2.5 text-sm outline-none focus:border-[#00A651]"
                        />
                      </div>
                      <div>
                        <label className="mb-1.5 block text-xs text-[#5A6F62]">
                          Mot de passe
                        </label>
                        <input
                          type="password"
                          value={wApiBasicPassword}
                          onChange={(e) => setWApiBasicPassword(e.target.value)}
                          className="w-full rounded-xl border border-[#E8EEE9] px-3.5 py-2.5 text-sm outline-none focus:border-[#00A651]"
                        />
                      </div>
                    </div>
                  )}

                  <div>
                    <label className="mb-1.5 block text-xs font-semibold uppercase text-[#5A6F62]">
                      Chemin vers les données dans la réponse JSON
                    </label>
                    <input
                      value={wApiResponseDataPath}
                      onChange={(e) => setWApiResponseDataPath(e.target.value)}
                      placeholder="ex. data.items (laisser vide si la réponse est directement une liste)"
                      className="w-full rounded-xl border border-[#E8EEE9] px-3.5 py-3 text-sm outline-none focus:border-[#00A651]"
                    />
                  </div>

                  <div>
                    <label className="mb-1.5 block text-xs font-semibold uppercase text-[#5A6F62]">
                      Fréquence de synchronisation
                    </label>
                    <select
                      value={wApiFrequency}
                      onChange={(e) => setWApiFrequency(e.target.value)}
                      className="w-full rounded-xl border border-[#E8EEE9] px-3.5 py-3 text-sm outline-none focus:border-[#00A651]"
                    >
                      <option value="manual">Manuelle</option>
                      <option value="hourly">Toutes les heures</option>
                      <option value="daily">Quotidienne</option>
                      <option value="realtime">Temps réel</option>
                    </select>
                  </div>

                  <div>
                    <label className="mb-1.5 flex items-center justify-between text-xs font-semibold uppercase text-[#5A6F62]">
                      <span>Mapping des champs</span>
                      <button
                        type="button"
                        onClick={addApiFieldMapRow}
                        className="rounded-md border border-[#DCE8E0] px-2 py-0.5 text-[11px] font-medium normal-case text-[#0B6B3A] hover:bg-[#E8F7EE]"
                      >
                        + Ajouter
                      </button>
                    </label>
                    <div className="space-y-2">
                      {wApiFieldMap.map((row, i) => (
                        <div key={i} className="flex items-center gap-2">
                          <input
                            value={row.source}
                            onChange={(e) =>
                              updateApiFieldMap(i, "source", e.target.value)
                            }
                            placeholder="champ source, ex. title"
                            className="w-1/2 rounded-xl border border-[#E8EEE9] px-3 py-2 text-sm outline-none focus:border-[#00A651]"
                          />
                          <span className="text-[#9AAB9F]">→</span>
                          <input
                            value={row.target}
                            onChange={(e) =>
                              updateApiFieldMap(i, "target", e.target.value)
                            }
                            placeholder="champ cible, ex. Titre"
                            className="w-1/2 rounded-xl border border-[#E8EEE9] px-3 py-2 text-sm outline-none focus:border-[#00A651]"
                          />
                          <button
                            type="button"
                            onClick={() => removeApiFieldMapRow(i)}
                            className="rounded-md border border-[#DCE8E0] px-2 py-1.5 text-xs text-[#B5473A] hover:bg-[#FBEAE7]"
                          >
                            ✕
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {step === 3 && (
                <div className="space-y-2 rounded-xl bg-[#F7FAF8] p-4 text-sm">
                  <p><span className="text-[#5A6F62]">Type :</span>{" "}
                    <strong>{SOURCE_TYPES.find((t) => t.type === selectedType)?.label}</strong>
                  </p>
                  {selectedType === "DOCUMENT" && previewUrl && wFile?.type.startsWith("image/") && (
                    <div className="mt-3 flex justify-center rounded-lg border border-[#E8EEE9] bg-white p-2">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src={previewUrl}
                        alt=""
                        className="max-h-[140px] rounded object-contain"
                      />
                    </div>
                  )}
                  {selectedType === "IOT" && (
                    <>
                      <p><span className="text-[#5A6F62]">Device UID :</span> <strong>{wIotDeviceUid || "—"}</strong></p>
                      <p><span className="text-[#5A6F62]">Type de capteur :</span> <strong>{iotDeviceTypeInfo.label}</strong></p>
                      <p><span className="text-[#5A6F62]">Protocole :</span> <strong>{IOT_PROTOCOLS.find((p) => p.value === wIotProtocol)?.label}</strong></p>
                    </>
                  )}
                  {selectedType === "API" && (
                    <>
                      <p><span className="text-[#5A6F62]">URL :</span> <strong>{wApiBaseUrl}/{wApiEndpointPath}</strong></p>
                      <p><span className="text-[#5A6F62]">Authentification :</span> <strong>{wApiAuthType}</strong></p>
                      <p><span className="text-[#5A6F62]">Catégorie :</span> <strong>{wApiCategory}</strong></p>
                    </>
                  )}
                  <p><span className="text-[#5A6F62]">Site :</span> <strong>{sites.find((s) => s.id === wSiteId)?.name}</strong></p>
                  <p className="pt-1 text-[12.5px] text-[#0B6B3A]">Catégorie & champs : détection automatique</p>
                </div>
              )}
            </div>

            <div className="flex justify-between border-t border-[#E8EEE9] px-6 py-4">
              <button
                type="button"
                onClick={() =>
                  step === 1 ? setWizardOpen(false) : setStep(step - 1)
                }
                className="rounded-xl border border-[#E8EEE9] px-5 py-2.5 text-sm font-medium text-[#1A2E22] hover:bg-[#F7FAF8]"
              >
                {step === 1 ? "Annuler" : "Retour"}
              </button>
              {step < 3 ? (
                <button
                  type="button"
                  disabled={
                    step === 1 ? !canContinueStep1 : !canContinueStep2
                  }
                  onClick={() => setStep(step + 1)}
                  className="rounded-xl bg-[#00A651] px-5 py-2.5 text-sm font-semibold text-white hover:bg-[#008F45] disabled:opacity-40"
                >
                  Continuer
                </button>
              ) : (
                <button
                  type="button"
                  disabled={saving || !canContinueStep2}
                  onClick={submitWizard}
                  className="rounded-xl bg-[#00A651] px-5 py-2.5 text-sm font-semibold text-white hover:bg-[#008F45] disabled:opacity-40"
                >
                  {saving
                    ? selectedType === "DOCUMENT"
                      ? "Extraction…"
                      : "Activation…"
                    : "Activer"}
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
