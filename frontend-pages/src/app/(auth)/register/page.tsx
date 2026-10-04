"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { register } from "@/features/auth/api";

export default function RegisterPage() {
  const router = useRouter();
  const [company, setCompany] = useState("");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await register({
        company_name: company.trim(),
        name: name.trim(),
        email: email.trim(),
        password,
      });
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Inscription impossible");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#EEF3F0] p-5">
      <form
        onSubmit={onSubmit}
        className="w-full max-w-[400px] rounded-2xl bg-white p-8 shadow-lg"
      >
        <h1 className="mb-1 text-xl font-bold text-[#0B6B3A]">Créer un compte</h1>
        <p className="mb-6 text-sm text-gray-500">Société + administrateur</p>

        {error && (
          <div className="mb-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </div>
        )}

        <label className="mb-1 block text-xs font-semibold uppercase text-gray-500">
          Société
        </label>
        <input
          required
          value={company}
          onChange={(e) => setCompany(e.target.value)}
          className="mb-3 w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2.5 text-sm outline-none focus:border-green-600"
        />

        <label className="mb-1 block text-xs font-semibold uppercase text-gray-500">
          Votre nom
        </label>
        <input
          required
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="mb-3 w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2.5 text-sm outline-none focus:border-green-600"
        />

        <label className="mb-1 block text-xs font-semibold uppercase text-gray-500">
          Email
        </label>
        <input
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="mb-3 w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2.5 text-sm outline-none focus:border-green-600"
        />

        <label className="mb-1 block text-xs font-semibold uppercase text-gray-500">
          Mot de passe
        </label>
        <input
          type="password"
          required
          minLength={6}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="mb-6 w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2.5 text-sm outline-none focus:border-green-600"
        />

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-lg bg-[#00A651] py-3 text-sm font-semibold text-white hover:bg-[#008F45] disabled:opacity-60"
        >
          {loading ? "Création…" : "Créer mon compte"}
        </button>

        <p className="mt-5 text-center text-sm text-gray-500">
          Déjà un compte ?{" "}
          <Link href="/login" className="font-semibold text-[#00A651]">
            Se connecter
          </Link>
        </p>
      </form>
    </div>
  );
}