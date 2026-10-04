"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  fetchPending,
  rejectExtraction,
  seedDemo,
  updateFields,
  validateExtraction,
  type Extraction,
} from "@/features/validation/api";
import { getAccessToken } from "@/features/auth/storage";

type ExtraField = { key: string; value: string };
type ViewTab = "documents" | "erp";

const HIDDEN_FIELD_KEYS = new Set(["_erp_record_id", "_category", "_erp_id"]);

function visibleFields(fields: Record<string, string> | undefined | null) {
  return Object.entries(fields || {}).filter(([key]) => !HIDDEN_FIELD_KEYS.has(key));
}

function formatValue(key: string, val: string): string {
  const num = Number(val);
  const looksNumeric =
    val !== "" && !isNaN(num) && /HT|TTC|TVA|Montant|Prix|Total/i.test(key);
  if (looksNumeric) {
    return num.toLocaleString("fr-FR", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  }
  return val;
}

export default function ValidationPage() {
  const router = useRouter();
  const [items, setItems] = useState<Extraction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [extraFields, setExtraFields] = useState<ExtraField[]>([]);
  const [tab, setTab] = useState<ViewTab>("documents");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  const load = useCallback(async () => {
    if (!getAccessToken()) {
      router.push("/login");
      return;
    }
    setLoading(true);
    setError("");
    try {
      setItems(await fetchPending());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur");
    } finally {
      setLoading(false);
    }
  }, [router]);

  useEffect(() => {
    load();
  }, [load]);

  async function onValidate(id: string) {
    await validateExtraction(id);
    setItems((prev) => prev.filter((x) => x.id !== id));
  }

  async function onReject(id: string) {
    await rejectExtraction(id);
    setItems((prev) => prev.filter((x) => x.id !== id));
  }

  function startEdit(item: Extraction) {
    setEditingId(item.id);
    const cleaned = Object.fromEntries(visibleFields(item.fields));
    setDraft(cleaned);
    setExtraFields([]);
  }

  function cancelEdit() {
    setEditingId(null);
    setExtraFields([]);
  }

  function addField() {
    setExtraFields((f) => [...f, { key: "", value: "" }]);
  }

  function updateExtraField(index: number, part: "key" | "value", val: string) {
    setExtraFields((f) =>
      f.map((entry, i) => (i === index ? { ...entry, [part]: val } : entry))
    );
  }

  function removeExtraField(index: number) {
    setExtraFields((f) => f.filter((_, i) => i !== index));
  }

  async function saveEdit(id: string) {
    const merged = { ...draft };
    for (const { key, value } of extraFields) {
      const trimmedKey = key.trim();
      if (trimmedKey) merged[trimmedKey] = value;
    }
    await updateFields(id, merged);
    await validateExtraction(id);
    setEditingId(null);
    setExtraFields([]);
    setItems((prev) => prev.filter((x) => x.id !== id));
  }

  async function onSeed() {
    await seedDemo();
    await load();
  }

  const ocrItems = items.filter((i) => i.doc_type !== "ERP");
  const erpItems = items.filter((i) => i.doc_type === "ERP");

  const erpColumns = Array.from(
    new Set(erpItems.flatMap((i) => visibleFields(i.fields).map(([k]) => k)))
  );

  function toggleSelect(id: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleSelectAll() {
    if (selectedIds.size === erpItems.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(erpItems.map((i) => i.id)));
    }
  }

  async function bulkValidate() {
    const ids = Array.from(selectedIds);
    for (const id of ids) {
      await validateExtraction(id);
    }
    setItems((prev) => prev.filter((x) => !selectedIds.has(x.id)));
    setSelectedIds(new Set());
  }

  async function bulkReject() {
    const ids = Array.from(selectedIds);
    for (const id of ids) {
      await rejectExtraction(id);
    }
    setItems((prev) => prev.filter((x) => !selectedIds.has(x.id)));
    setSelectedIds(new Set());
  }

  return (
    <>
      <header className="flex items-center justify-between border-b border-[#DCE8E0] bg-white px-7 py-3.5">
        <div className="flex gap-2">
          {[
            { id: "documents" as ViewTab, label: `Documents (${ocrItems.length})` },
            { id: "erp" as ViewTab, label: `Données ERP (${erpItems.length})` },
          ].map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setTab(t.id)}
              className={`border-b-2 px-3 py-2.5 text-sm font-semibold ${
                tab === t.id
                  ? "border-[#00A651] text-[#00A651]"
                  : "border-transparent text-[#5A6F62] hover:text-[#1A2E22]"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
        <div>
          <h1 className="text-[18px] font-bold text-[#1A2E22]">Validation</h1>
          <p className="mt-0.5 text-[12.5px] text-[#5A6F62]">
            Extractions à valider avant intégration au référentiel
          </p>
        </div>
        <button
          type="button"
          onClick={onSeed}
          className="rounded-lg border border-[#DCE8E0] px-3.5 py-2 text-sm font-medium text-[#1A2E22] hover:bg-[#E8F7EE]"
        >
          Charger 2 démos
        </button>
      </header>

      <div className="flex-1 overflow-y-auto p-6">
        {error && (
          <div className="mb-4 rounded-lg bg-[#FBEAE7] px-3 py-2 text-sm text-[#B5473A]">
            {error}
          </div>
        )}

        {loading ? (
          <p className="text-sm text-[#5A6F62]">Chargement…</p>
        ) : items.length === 0 ? (
          <div className="rounded-xl border border-[#DCE8E0] bg-white p-10 text-center">
            <p className="text-sm text-[#5A6F62]">Aucune extraction en attente.</p>
            <button
              type="button"
              onClick={onSeed}
              className="mt-4 rounded-lg bg-[#00A651] px-4 py-2 text-sm font-semibold text-white hover:bg-[#008F45]"
            >
              Charger des exemples
            </button>
          </div>
        ) : (
          <>
            {tab === "documents" && (
              <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                {ocrItems.map((item) => (
                  <article
                    key={item.id}
                    className="rounded-xl border border-[#DCE8E0] bg-white p-5 shadow-[0_4px_16px_rgba(11,107,58,0.06)]"
                  >
                    <div className="mb-3 flex items-start justify-between gap-3">
                      <div>
                        <h3 className="text-sm font-bold text-[#1A2E22]">
                          {item.filename}
                        </h3>
                        <p className="mt-0.5 text-[12.5px] text-[#5A6F62]">
                          {item.doc_type} · {item.category}
                        </p>
                      </div>
                      <span className="shrink-0 rounded-md bg-[#EAF2F8] px-2.5 py-1 text-xs font-semibold text-[#3D7AA8]">
                        {Math.round(item.confidence * 100)} % confiance
                      </span>
                    </div>

                    <div className="mb-3 space-y-2 rounded-lg bg-[#F5F8F6] p-3">
                      {visibleFields(
                        editingId === item.id ? draft : item.fields
                      ).map(([key, val]) => (
                        <div
                          key={key}
                          className="flex items-center justify-between gap-3 text-[13px]"
                        >
                          <span className="text-[#5A6F62]">{key}</span>
                          {editingId === item.id ? (
                            <input
                              value={draft[key] ?? ""}
                              onChange={(e) =>
                                setDraft((d) => ({
                                  ...d,
                                  [key]: e.target.value,
                                }))
                              }
                              className="max-w-[55%] rounded border border-[#DCE8E0] px-2 py-1 text-right text-[#1A2E22] outline-none focus:border-[#00A651]"
                            />
                          ) : (
                            <span className="font-medium text-[#1A2E22]">
                              {formatValue(key, val)}
                            </span>
                          )}
                        </div>
                      ))}
                    </div>

                    {editingId === item.id && (
                      <div className="mb-3 space-y-2 rounded-lg border border-dashed border-[#DCE8E0] p-3">
                        {extraFields.length > 0 && (
                          <p className="mb-1 text-[11px] font-medium uppercase tracking-wide text-[#5A6F62]">
                            Champs ajoutés manuellement
                          </p>
                        )}
                        {extraFields.map((entry, index) => (
                          <div key={index} className="flex items-center gap-2">
                            <input
                              value={entry.key}
                              onChange={(e) =>
                                updateExtraField(index, "key", e.target.value)
                              }
                              placeholder="Nom du champ"
                              className="w-2/5 rounded border border-[#DCE8E0] px-2 py-1 text-[13px] text-[#1A2E22] outline-none focus:border-[#00A651]"
                            />
                            <input
                              value={entry.value}
                              onChange={(e) =>
                                updateExtraField(index, "value", e.target.value)
                              }
                              placeholder="Valeur"
                              className="flex-1 rounded border border-[#DCE8E0] px-2 py-1 text-[13px] text-[#1A2E22] outline-none focus:border-[#00A651]"
                            />
                            <button
                              type="button"
                              onClick={() => removeExtraField(index)}
                              aria-label="Supprimer ce champ"
                              className="shrink-0 rounded px-2 py-1 text-[13px] text-[#B5473A] hover:bg-[#FBEAE7]"
                            >
                              ×
                            </button>
                          </div>
                        ))}
                        <button
                          type="button"
                          onClick={addField}
                          className="mt-1 w-full rounded-lg border border-dashed border-[#00A651] px-3 py-2 text-xs font-semibold text-[#00A651] hover:bg-[#E8F7EE]"
                        >
                          + Ajouter un champ
                        </button>
                      </div>
                    )}

                    <div className="flex flex-wrap gap-2">
                      {editingId === item.id ? (
                        <>
                          <button
                            type="button"
                            onClick={() => saveEdit(item.id)}
                            className="rounded-lg bg-[#00A651] px-3.5 py-2 text-xs font-semibold text-white hover:bg-[#008F45]"
                          >
                            Enregistrer & valider
                          </button>
                          <button
                            type="button"
                            onClick={cancelEdit}
                            className="rounded-lg border border-[#DCE8E0] px-3.5 py-2 text-xs font-medium text-[#1A2E22] hover:bg-[#E8F7EE]"
                          >
                            Annuler
                          </button>
                        </>
                      ) : (
                        <>
                          <button
                            type="button"
                            onClick={() => onValidate(item.id)}
                            className="rounded-lg bg-[#00A651] px-3.5 py-2 text-xs font-semibold text-white hover:bg-[#008F45]"
                          >
                            Valider
                          </button>
                          <button
                            type="button"
                            onClick={() => startEdit(item)}
                            className="rounded-lg border border-[#DCE8E0] px-3.5 py-2 text-xs font-medium text-[#1A2E22] hover:bg-[#E8F7EE]"
                          >
                            Corriger
                          </button>
                          <button
                            type="button"
                            onClick={() => onReject(item.id)}
                            className="rounded-lg border border-[#DCE8E0] px-3.5 py-2 text-xs font-medium text-[#B5473A] hover:bg-[#FBEAE7]"
                          >
                            Rejeter
                          </button>
                        </>
                      )}
                    </div>
                  </article>
                ))}
              </div>
            )}

            {tab === "erp" && (
              <div className="overflow-hidden rounded-xl border border-[#DCE8E0] bg-white">
                {erpItems.length === 0 ? (
                  <p className="p-10 text-center text-sm text-[#5A6F62]">
                    Aucune donnée ERP en attente. Synchronisez une source ERP
                    depuis la page Sources.
                  </p>
                ) : (
                  <>
                    {selectedIds.size > 0 && (
                      <div className="flex items-center justify-between border-b border-[#DCE8E0] bg-[#E8F7EE] px-4 py-2.5">
                        <span className="text-sm font-medium text-[#0B6B3A]">
                          {selectedIds.size} ligne(s) sélectionnée(s)
                        </span>
                        <div className="flex gap-2">
                          <button
                            type="button"
                            onClick={bulkValidate}
                            className="rounded-lg bg-[#00A651] px-3.5 py-1.5 text-xs font-semibold text-white hover:bg-[#008F45]"
                          >
                            Valider la sélection
                          </button>
                          <button
                            type="button"
                            onClick={bulkReject}
                            className="rounded-lg border border-[#DCE8E0] px-3.5 py-1.5 text-xs font-medium text-[#B5473A] hover:bg-[#FBEAE7]"
                          >
                            Rejeter la sélection
                          </button>
                        </div>
                      </div>
                    )}
                    <div className="overflow-x-auto">
                      <table className="w-full border-collapse text-left text-[13px]">
                        <thead>
                          <tr className="bg-[#E8F7EE] text-[11px] font-semibold uppercase text-[#5A6F62]">
                            <th className="px-3 py-2.5">
                              <input
                                type="checkbox"
                                checked={
                                  selectedIds.size === erpItems.length &&
                                  erpItems.length > 0
                                }
                                onChange={toggleSelectAll}
                              />
                            </th>
                            <th className="px-3 py-2.5">Catégorie</th>
                            {erpColumns.map((col) => (
                              <th key={col} className="px-3 py-2.5">
                                {col}
                              </th>
                            ))}
                            <th className="px-3 py-2.5" />
                          </tr>
                        </thead>
                        <tbody>
                          {erpItems.map((item) => {
                            const fieldMap = Object.fromEntries(
                              visibleFields(item.fields)
                            );
                            return (
                              <tr
                                key={item.id}
                                className="border-t border-[#DCE8E0] hover:bg-[#FAFBF9]"
                              >
                                <td className="px-3 py-2.5">
                                  <input
                                    type="checkbox"
                                    checked={selectedIds.has(item.id)}
                                    onChange={() => toggleSelect(item.id)}
                                  />
                                </td>
                                <td className="px-3 py-2.5">
                                  <span className="rounded-md bg-[#EEF3EF] px-2 py-0.5 text-xs font-semibold text-[#3D8B5F]">
                                    {item.category}
                                  </span>
                                </td>
                                {erpColumns.map((col) => (
                                  <td
                                    key={col}
                                    className="px-3 py-2.5 text-[#1A2E22]"
                                  >
                                    {fieldMap[col] ?? "—"}
                                  </td>
                                ))}
                                <td className="px-3 py-2.5">
                                  <div className="flex gap-1.5">
                                    <button
                                      type="button"
                                      onClick={() => onValidate(item.id)}
                                      className="rounded px-2 py-1 text-xs font-medium text-[#00A651] hover:bg-[#E8F7EE]"
                                    >
                                      ✓
                                    </button>
                                    <button
                                      type="button"
                                      onClick={() => onReject(item.id)}
                                      className="rounded px-2 py-1 text-xs font-medium text-[#B5473A] hover:bg-[#FBEAE7]"
                                    >
                                      ✕
                                    </button>
                                  </div>
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  </>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </>
  );
}