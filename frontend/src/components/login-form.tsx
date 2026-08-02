"use client";

import { FormEvent, useState } from "react";
import { ArrowRight, Cube, LockKey } from "@phosphor-icons/react";

import { isInsForgeConfigured, insforge } from "@/lib/insforge";

interface LoginFormProps {
  onAuthenticated: (user: AuthUser, accessToken: string) => void;
}

export interface AuthUser {
  id: string;
  email: string;
}

export function LoginForm({ onAuthenticated }: LoginFormProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    if (!isInsForgeConfigured) {
      setError("Add NEXT_PUBLIC_INSFORGE_BASE_URL before signing in.");
      return;
    }

    setIsSubmitting(true);
    try {
      const { data, error: authError } =
        await insforge.auth.signInWithPassword({ email, password });

      if (authError || !data?.user || !data.accessToken) {
        throw authError ?? new Error("InsForge did not return a session.");
      }
      onAuthenticated(
        { id: data.user.id, email: data.user.email },
        data.accessToken,
      );
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : "Sign in failed. Check your credentials.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="min-h-[100dvh] px-4 py-6 sm:px-8 sm:py-8">
      <div className="mx-auto grid min-h-[calc(100dvh-3rem)] max-w-6xl overflow-hidden rounded-[2rem] border border-emerald-950/10 bg-white shadow-[0_28px_90px_-54px_rgba(24,33,29,0.5)] sm:min-h-[calc(100dvh-4rem)] md:grid-cols-[1.08fr_0.92fr]">
        <section className="relative hidden overflow-hidden bg-ink p-12 text-white md:flex md:flex-col md:justify-between">
          <div className="absolute -right-36 top-16 h-80 w-80 rounded-full border border-white/10" />
          <div className="absolute -right-16 top-36 h-44 w-44 rounded-full border border-accent/70" />
          <div className="relative flex items-center gap-3">
            <span className="grid h-9 w-9 place-items-center rounded-xl border border-white/15 bg-white/10">
              <Cube aria-hidden size={19} weight="duotone" />
            </span>
            <span className="text-sm font-semibold tracking-tight">
              AI Kubernetes Agent
            </span>
          </div>
          <div className="relative max-w-lg pb-8">
            <p className="font-mono text-xs uppercase tracking-[0.2em] text-emerald-300/80">
              Cluster investigation workspace
            </p>
            <h1 className="mt-6 text-4xl font-semibold leading-[1.02] tracking-[-0.04em] sm:text-5xl">
              Find the failure. Understand the fix.
            </h1>
            <p className="mt-6 max-w-[48ch] text-sm leading-relaxed text-emerald-50/60">
              Inspect Kubernetes evidence and turn it into a clear, actionable diagnosis.
            </p>
          </div>
        </section>

        <section className="flex items-center px-6 py-12 sm:px-12 lg:px-16">
          <div className="w-full max-w-sm">
            <div className="mb-10 flex items-center gap-3 md:hidden">
              <span className="grid h-9 w-9 place-items-center rounded-xl bg-ink text-white">
                <Cube aria-hidden size={19} weight="duotone" />
              </span>
              <span className="text-sm font-semibold text-ink">
                AI Kubernetes Agent
              </span>
            </div>
            <LockKey aria-hidden className="text-accent" size={24} weight="duotone" />
            <h2 className="mt-5 text-3xl font-semibold tracking-[-0.035em] text-ink">
              Sign in
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-emerald-950/55">
              Use your InsForge account to access investigations and history.
            </p>

            <form className="mt-9 space-y-5" onSubmit={handleSubmit}>
              <label className="block">
                <span className="mb-2 block text-sm font-medium text-ink">Email</span>
                <input
                  autoComplete="email"
                  className="w-full rounded-xl border border-emerald-950/15 bg-canvas/55 px-4 py-3 text-sm text-ink outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/15"
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="you@example.com"
                  required
                  type="email"
                  value={email}
                />
              </label>
              <label className="block">
                <span className="mb-2 block text-sm font-medium text-ink">Password</span>
                <input
                  autoComplete="current-password"
                  className="w-full rounded-xl border border-emerald-950/15 bg-canvas/55 px-4 py-3 text-sm text-ink outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/15"
                  minLength={8}
                  onChange={(event) => setPassword(event.target.value)}
                  required
                  type="password"
                  value={password}
                />
              </label>

              {error ? (
                <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm leading-relaxed text-red-700" role="alert">
                  {error}
                </p>
              ) : null}

              <button
                className="flex w-full items-center justify-between rounded-xl bg-ink px-5 py-3.5 text-sm font-semibold text-white transition duration-300 ease-out hover:-translate-y-0.5 hover:bg-emerald-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-4 active:translate-y-px disabled:cursor-not-allowed disabled:opacity-60"
                disabled={isSubmitting}
                type="submit"
              >
                <span>{isSubmitting ? "Signing in..." : "Sign in to dashboard"}</span>
                <ArrowRight aria-hidden size={17} weight="bold" />
              </button>
            </form>
          </div>
        </section>
      </div>
    </main>
  );
}
