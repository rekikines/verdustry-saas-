"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { login } from "@/features/auth/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email.trim(), password);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur de connexion");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#EEF3F0] p-5">
      <div className="w-full max-w-[420px] overflow-hidden rounded-[20px] bg-white shadow-[0_20px_50px_rgba(11,107,58,0.15),0_4px_12px_rgba(0,0,0,0.06)]">
        {/* Header dégradé — style prototype */}
        <div className="relative overflow-hidden bg-gradient-to-br from-[#00A651] via-[#0B7A3E] to-[#086B36] px-7 pb-7 pt-8 text-center">
          <div className="pointer-events-none absolute -right-8 -top-10 h-40 w-40 rounded-full bg-white/15" />
          <div className="pointer-events-none absolute -bottom-12 -left-10 h-36 w-36 rounded-full bg-white/10" />

          <div className="relative z-10 mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-[14px] bg-white shadow-[0_4px_14px_rgba(0,0,0,0.12)]">
            <span className="text-2xl font-extrabold text-[#0B6B3A]">V</span>
          </div>
          <h1 className="relative z-10 text-[22px] font-bold text-white">Verdustry</h1>
          <p className="relative z-10 mx-auto mt-1.5 max-w-[280px] text-[13.5px] leading-snug text-white/90">
            Connectez-vous à votre espace data environnemental
          </p>
        </div>

        {/* Formulaire */}
        <form onSubmit={onSubmit} className="px-7 pb-6 pt-7">
          {error && (
            <div className="mb-3 rounded-lg bg-[#FBEAE7] px-3 py-2 text-[12.5px] text-[#B5473A]">
              {error}
            </div>
          )}

          <div className="mb-3.5">
            <label className="mb-1.5 block text-[11.5px] font-semibold uppercase tracking-wide text-[#5A6F62]">
              Email
            </label>
            <div className="flex items-center gap-2.5 rounded-[10px] border border-[#DCE8E0] bg-[#F4F7F5] px-3.5 transition focus-within:border-[#00A651] focus-within:bg-white focus-within:shadow-[0_0_0_3px_rgba(0,166,81,0.12)]">
              <span className="text-[#3D8B5F]">✉</span>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="vous@entreprise.com"
                className="w-full border-0 bg-transparent py-3 text-sm text-[#1A2E22] outline-none placeholder:text-[#9AAB9F]"
              />
            </div>
          </div>

          <div className="mb-4">
            <label className="mb-1.5 block text-[11.5px] font-semibold uppercase tracking-wide text-[#5A6F62]">
              Mot de passe
            </label>
            <div className="flex items-center gap-2.5 rounded-[10px] border border-[#DCE8E0] bg-[#F4F7F5] px-3.5 transition focus-within:border-[#00A651] focus-within:bg-white focus-within:shadow-[0_0_0_3px_rgba(0,166,81,0.12)]">
              <span className="text-[#3D8B5F]">🔒</span>
              <input
                type="password"
                required
                minLength={6}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full border-0 bg-transparent py-3 text-sm text-[#1A2E22] outline-none placeholder:text-[#9AAB9F]"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="mt-1.5 flex w-full items-center justify-center gap-2 rounded-[10px] bg-[#00A651] py-3.5 text-[14.5px] font-semibold text-white transition hover:bg-[#008F45] active:scale-[0.98] disabled:opacity-60"
          >
            {loading ? "Connexion…" : "Se connecter"}
          </button>

          <div className="my-5 flex items-center gap-3 text-xs font-medium text-[#5A6F62]">
            <span className="h-px flex-1 bg-[#DCE8E0]" />
            ou
            <span className="h-px flex-1 bg-[#DCE8E0]" />
          </div>

          <p className="text-center text-[13.5px] text-[#5A6F62]">
            Pas de compte ?{" "}
            <Link href="/register" className="font-semibold text-[#00A651] hover:text-[#008F45]">
              Créer un compte
            </Link>
          </p>
        </form>

        <p className="pb-5 text-center text-[11.5px] text-[#5A6F62]">
          Verdustry — Gestion data ESG
        </p>
      </div>
    </div>
  );
}