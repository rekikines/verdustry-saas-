"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { fetchMe, logout } from "@/features/auth/api";
import type { AuthUser } from "@/features/auth/types";

const nav = [
  { href: "/dashboard", label: "Tableau de bord", icon: "▦" },
  { href: "/sources", label: "Sources de données", icon: "⬡" },
  { href: "/sites", label: "Sites", icon: "◎" },
  { href: "/validation", label: "Validation", icon: "✓" },
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null>(null);

  useEffect(() => {
    fetchMe()
      .then(setUser)
      .catch(() => router.push("/login"));
  }, [router]);

  const initials = user?.name
    ? user.name
        .split(" ")
        .map((p) => p[0])
        .join("")
        .slice(0, 2)
        .toUpperCase()
    : "…";

  return (
    <div className="flex min-h-screen bg-[#F5F8F6] text-[14px] text-[#1A2E22]">
      {/* Sidebar prototype */}
      <aside className="flex w-[248px] shrink-0 flex-col bg-[#0B6B3A] text-white">
        <div className="flex items-center gap-[11px] px-5 pb-[18px] pt-[22px]">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[10px] bg-white text-base font-extrabold text-[#0B6B3A] shadow-[0_2px_8px_rgba(0,0,0,0.12)]">
            V
          </div>
          <div>
            <div className="text-[15.5px] font-bold leading-tight">Verdustry</div>
            <div className="mt-0.5 text-[9.5px] tracking-wide text-[#8FBF9F]">
              Gestion Data ESG
            </div>
          </div>
        </div>

        {/* Profil */}
        <div className="mb-2 flex items-center gap-2.5 border-b border-white/10 px-5 pb-[18px] pt-3.5">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-[#7BC99A] to-[#5FA876] text-[13px] font-bold text-[#0B6B3A]">
            {initials}
          </div>
          <div className="min-w-0">
            <div className="truncate text-[13px] font-semibold text-white">
              {user?.name || "…"}
            </div>
            <div className="text-[11px] text-[#9FBFA9]">{user?.role || "—"}</div>
          </div>
        </div>

        <nav className="flex flex-1 flex-col gap-0.5 overflow-y-auto px-2.5">
          <div className="px-3.5 pb-1.5 pt-3.5 text-[10px] font-semibold uppercase tracking-[0.06em] text-[#7A9E88]">
            Navigation
          </div>
          {nav.map((item) => {
            const active = pathname === item.href || pathname.startsWith(item.href + "/");
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex w-full items-center gap-2.5 rounded-lg px-3.5 py-2.5 text-left text-[13.5px] transition ${
                  active
                    ? "bg-[#00A651] font-semibold text-white"
                    : "text-[#CFE3D6] hover:bg-[#0D7A42] hover:text-white"
                }`}
              >
                <span className="w-[18px] text-center text-[13px]">{item.icon}</span>
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="border-t border-white/10 p-2.5 pb-4">
          <button
            type="button"
            onClick={() => {
              logout();
              router.push("/login");
            }}
            className="flex w-full items-center gap-2.5 rounded-lg px-3.5 py-2.5 text-[13.5px] text-[#CFE3D6] hover:bg-[#0D7A42] hover:text-white"
          >
            <span className="w-[18px] text-center">⏻</span>
            Déconnexion
          </button>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">{children}</div>
    </div>
  );
}