"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  createSite,
  deleteSite,
  fetchSites,
  type Site,
} from "@/features/sites/api";
import { getAccessToken } from "@/features/auth/storage";

export default function SitesPage() {
  const router = useRouter();
  const [sites, setSites] = useState<Site[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [name, setName] = useState("");
  const [location, setLocation] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    if (!getAccessToken()) {
      router.push("/login");
      return;
    }
    setLoading(true);
    setError("");
    try {
      setSites(await fetchSites());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur");
    } finally {
      setLoading(false);
    }
  }, [router]);

  useEffect(() => {
    load();
  }, [load]);

  async function onCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setSaving(true);
    setError("");
    try {
      await createSite({ name: name.trim(), location: location.trim() || undefined });
      setName("");
      setLocation("");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur création");
    } finally {
      setSaving(false);
    }
  }

  async function onDelete(id: string) {
    if (!confirm("Supprimer ce site ?")) return;
    try {
      await deleteSite(id);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur suppression");
    }
  }

  return (
    <>
      <header className="flex items-center justify-between border-b border-[#DCE8E0] bg-white px-7 py-3.5">
        <div>
          <h1 className="text-lg font-bold text-[#1A2E22]">Sites industriels</h1>
          <p className="mt-0.5 text-[12.5px] text-[#5A6F62]">
            Isolés par société (multi-tenant)
          </p>
        </div>
      </header>

      <div className="flex-1 overflow-y-auto p-6">
        {error && (
          <div className="mb-4 rounded-lg bg-[#FBEAE7] px-3 py-2 text-sm text-[#B5473A]">
            {error}
          </div>
        )}

        {/* Formulaire ajout */}
        <form
          onSubmit={onCreate}
          className="mb-5 rounded-xl border border-[#DCE8E0] bg-white p-5"
        >
          <h2 className="mb-3 text-sm font-bold text-[#1A2E22]">Ajouter un site</h2>
          <div className="flex flex-wrap gap-3">
            <input
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Nom du site (ex. Usine Sousse Nord)"
              className="min-w-[220px] flex-1 rounded-lg border border-[#DCE8E0] px-3 py-2 text-sm outline-none focus:border-[#00A651]"
            />
            <input
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              placeholder="Localisation (optionnel)"
              className="min-w-[180px] flex-1 rounded-lg border border-[#DCE8E0] px-3 py-2 text-sm outline-none focus:border-[#00A651]"
            />
            <button
              type="submit"
              disabled={saving}
              className="rounded-lg bg-[#00A651] px-4 py-2 text-sm font-semibold text-white hover:bg-[#008F45] disabled:opacity-60"
            >
              {saving ? "…" : "+ Ajouter"}
            </button>
          </div>
        </form>

        {/* Liste */}
        <div className="overflow-hidden rounded-xl border border-[#DCE8E0] bg-white">
          <table className="w-full border-collapse text-left">
            <thead>
              <tr className="bg-[#E8F7EE] text-[11.5px] font-semibold uppercase tracking-wide text-[#5A6F62]">
                <th className="px-3.5 py-2.5">Nom</th>
                <th className="px-3.5 py-2.5">Localisation</th>
                <th className="px-3.5 py-2.5">ID</th>
                <th className="px-3.5 py-2.5" />
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={4} className="px-3.5 py-8 text-center text-sm text-[#5A6F62]">
                    Chargement…
                  </td>
                </tr>
              ) : sites.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-3.5 py-8 text-center text-sm text-[#5A6F62]">
                    Aucun site — créez le premier ci-dessus.
                  </td>
                </tr>
              ) : (
                sites.map((s) => (
                  <tr
                    key={s.id}
                    className="border-t border-[#DCE8E0] text-[13.5px] hover:bg-[#FAFBF9]"
                  >
                    <td className="px-3.5 py-3 font-medium text-[#1A2E22]">{s.name}</td>
                    <td className="px-3.5 py-3 text-[#5A6F62]">{s.location || "—"}</td>
                    <td className="px-3.5 py-3 font-mono text-xs text-[#5A6F62]">{s.id}</td>
                    <td className="px-3.5 py-3 text-right">
                      <button
                        type="button"
                        onClick={() => onDelete(s.id)}
                        className="rounded-md border border-[#DCE8E0] px-2.5 py-1 text-xs text-[#B5473A] hover:bg-[#FBEAE7]"
                      >
                        Supprimer
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}