"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { fetchMe } from "@/features/auth/api";
import type { AuthUser } from "@/features/auth/types";
import {
  fetchDashboardStats,
  type DashboardStats,
} from "@/features/dashboard/api";
import IoTLiveChartCard from "@/features/iot/IoTLiveChartCard";

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([fetchMe(), fetchDashboardStats()])
      .then(([u, s]) => {
        setUser(u);
        setStats(s);
      })
      .catch(() => router.push("/login"));
  }, [router]);

  if (!user || !stats) {
    return (
      <div className="flex flex-1 items-center justify-center text-[#5A6F62]">
        Chargement…
      </div>
    );
  }

  const firstName = user.name.split(" ")[0];

  const cards = [
    {
      label: "Sources actives",
      value: String(stats.active_sources),
      sub: `${stats.total_sources} configurée(s) au total`,
      warn: false,
    },
    {
      label: "Sources OCR",
      value: String(stats.ocr_pending_sources),
      sub: "En attente d'extraction",
      warn: stats.ocr_pending_sources > 0,
    },
    {
      label: "À valider",
      value: String(stats.pending_validation),
      sub: "Extractions en attente",
      warn: stats.pending_validation > 0,
    },
    {
      label: "Sites",
      value: String(stats.sites_count),
      sub: "Sites industriels",
      warn: false,
    },
  ];

  return (
    <>
      <header className="flex items-center justify-between border-b border-[#DCE8E0] bg-white px-7 py-3.5">
        <div>
          <h1 className="text-[18px] font-bold text-[#1A2E22]">Tableau de bord</h1>
          <p className="mt-0.5 text-[12.5px] text-[#5A6F62]">
            {user.name} · {user.role}
          </p>
        </div>
      </header>

      <div className="flex-1 overflow-y-auto p-6">
        {error && (
          <div className="mb-4 rounded-lg bg-[#FBEAE7] px-3 py-2 text-sm text-[#B5473A]">
            {error}
          </div>
        )}

        {/* Hero */}
        <div className="relative mb-5 overflow-hidden rounded-2xl bg-gradient-to-br from-[#00A651] via-[#0B7A3E] to-[#086B36] px-7 py-7 text-white">
          <div className="pointer-events-none absolute -right-10 -top-14 h-56 w-56 rounded-full bg-white/10" />
          <h2 className="relative z-10 text-[22px] font-bold">
            Bonjour {firstName}
          </h2>
          <p className="relative z-10 mt-1 text-[13.5px] text-[#CFE3D6]">
            {stats.active_sources} source(s) active(s) ·{" "}
            {stats.pending_validation} validation(s) en attente
          </p>

          <div className="relative z-10 mt-5 flex flex-wrap gap-2.5">
            <Link
              href="/sources"
              className="inline-flex items-center rounded-lg bg-[#00A651] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#008F45]"
            >
              + Connecter une source
            </Link>
            <Link
              href="/validation"
              className="inline-flex items-center rounded-lg border border-white/25 bg-white/10 px-4 py-2.5 text-sm font-semibold text-white hover:bg-white/20"
            >
              Voir les validations
              {stats.pending_validation > 0 && (
                <span className="ml-2 rounded-full bg-[#B5473A] px-2 py-0.5 text-[11px]">
                  {stats.pending_validation}
                </span>
              )}
            </Link>
          </div>
        </div>

        {/* Stats réelles */}
        <div className="mb-5 grid grid-cols-1 gap-3.5 sm:grid-cols-2 lg:grid-cols-4">
          {cards.map((s) => (
            <div
              key={s.label}
              className="rounded-xl border border-[#DCE8E0] bg-white px-[18px] py-4 transition hover:shadow-[0_4px_16px_rgba(11,107,58,0.07)]"
            >
              <div className="mb-1.5 text-xs text-[#5A6F62]">{s.label}</div>
              <div
                className={`text-2xl font-bold ${
                  s.warn ? "text-[#C98A2C]" : "text-[#0B6B3A]"
                }`}
              >
                {s.value}
              </div>
              <div className="mt-1 text-[11.5px] text-[#5A6F62]">{s.sub}</div>
            </div>
          ))}
        </div>

        {/* Indicateurs par catégorie — toutes sources confondues */}
        {stats.category_breakdown.length > 0 && (
          <div className="mb-5 overflow-hidden rounded-xl border border-[#DCE8E0] bg-white">
            <div className="border-b border-[#E8EEE9] px-5 py-3.5">
              <h3 className="text-sm font-bold text-[#1A2E22]">
                Indicateurs par catégorie
              </h3>
              <p className="mt-0.5 text-[12px] text-[#5A6F62]">
                Toutes sources confondues (ERP, IoT, documents, saisie manuelle…)
              </p>
            </div>
            <table className="w-full border-collapse text-left text-[13px]">
              <thead>
                <tr className="bg-[#F5F8F6] text-[11px] font-semibold uppercase text-[#5A6F62]">
                  <th className="px-5 py-2.5">Catégorie</th>
                  <th className="px-5 py-2.5">Sources actives</th>
                  <th className="px-5 py-2.5">Enregistrements collectés</th>
                </tr>
              </thead>
              <tbody>
                {stats.category_breakdown.map((c) => (
                  <tr key={c.category} className="border-t border-[#E8EEE9]">
                    <td className="px-5 py-2.5">
                      <span className="rounded-md bg-[#EEF3EF] px-2.5 py-1 text-xs font-semibold text-[#3D8B5F]">
                        {c.category}
                      </span>
                    </td>
                    <td className="px-5 py-2.5 text-[#1A2E22]">
                      {c.active_sources_count} / {c.sources_count}
                    </td>
                    <td className="px-5 py-2.5 text-[#1A2E22]">{c.records_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Capteur IoT sélectionné, avec sa courbe temps réel */}
        <IoTLiveChartCard />

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <div className="rounded-xl border border-[#DCE8E0] bg-white p-5">
            <h3 className="mb-1 text-sm font-bold text-[#1A2E22]">Contexte</h3>
            <ul className="space-y-1.5 text-[13px]">
              <li>
              </li>

            </ul>
          </div>

          <div className="rounded-xl border border-[#DCE8E0] bg-white p-5">
            <h3 className="mb-1 text-sm font-bold text-[#1A2E22]">Raccourcis</h3>
            <p className="mb-3 text-[12.5px] text-[#5A6F62]">Modules prêts</p>
            <div className="flex flex-wrap gap-2">
              <Link
                href="/sources"
                className="rounded-lg border border-[#DCE8E0] px-3 py-1.5 text-xs font-medium hover:bg-[#E8F7EE]"
              >
                Sources
              </Link>
              <Link
                href="/sites"
                className="rounded-lg border border-[#DCE8E0] px-3 py-1.5 text-xs font-medium hover:bg-[#E8F7EE]"
              >
                Sites
              </Link>
              <Link
                href="/validation"
                className="rounded-lg border border-[#DCE8E0] px-3 py-1.5 text-xs font-medium hover:bg-[#E8F7EE]"
              >
                Validation
              </Link>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
