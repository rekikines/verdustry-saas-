"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { fetchMe, logout } from "@/features/auth/api";
import type { AuthUser } from "@/features/auth/types";

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchMe()
      .then(setUser)
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Erreur");
        router.push("/login");
      });
  }, [router]);

  function onLogout() {
    logout();
    router.push("/login");
  }

  if (!user) {
    return (
      <div className="flex min-h-screen items-center justify-center text-gray-500">
        {error || "Chargement…"}
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#F5F8F6] p-8">
      <div className="mx-auto max-w-2xl rounded-2xl bg-white p-8 shadow">
        <h1 className="text-2xl font-bold text-[#0B6B3A]">Dashboard</h1>
        <p className="mt-2 text-gray-600">
          Bonjour <strong>{user.name}</strong>
        </p>
        <ul className="mt-4 space-y-1 text-sm text-gray-700">
          <li>Email : {user.email}</li>
          <li>Rôle : {user.role}</li>
          <li>Société : {user.company_id}</li>
          <li>Site : {user.site_id || "—"}</li>
        </ul>
        <button
          onClick={onLogout}
          className="mt-6 rounded-lg bg-[#0B6B3A] px-4 py-2 text-sm font-semibold text-white"
        >
          Déconnexion
        </button>
      </div>
    </div>
  );
}