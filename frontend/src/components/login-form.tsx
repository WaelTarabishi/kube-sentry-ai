"use client";

import { FormEvent, useState } from "react";
import {
  ArrowRight,
  CheckCircle,
  Cube,
  EnvelopeSimple,
  LockKey,
  UserPlus,
} from "@phosphor-icons/react";

import { isInsForgeConfigured, insforge } from "@/lib/insforge";

interface LoginFormProps {
  onAuthenticated: (user: AuthUser, accessToken: string) => void;
}

export interface AuthUser {
  id: string;
  email: string;
}

type AuthMode = "sign-in" | "register" | "verify";

export function LoginForm({ onAuthenticated }: LoginFormProps) {
  const [mode, setMode] = useState<AuthMode>("sign-in");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [verificationEmail, setVerificationEmail] = useState("");
  const [verificationCode, setVerificationCode] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isResending, setIsResending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  function changeMode(nextMode: Exclude<AuthMode, "verify">) {
    setMode(nextMode);
    setError(null);
    setNotice(null);
    setPassword("");
    setConfirmPassword("");
  }

  async function handleAuthSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setNotice(null);

    if (!isInsForgeConfigured) {
      setError("Add NEXT_PUBLIC_INSFORGE_BASE_URL before continuing.");
      return;
    }

    if (mode === "register" && password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setIsSubmitting(true);
    try {
      if (mode === "register") {
        const { data, error: authError } = await insforge.auth.signUp({
          email,
          password,
          name: name.trim() || undefined,
        });

        if (authError || !data) {
          throw authError ?? new Error("InsForge did not create the account.");
        }

        if (data.user && data.accessToken) {
          onAuthenticated(
            { id: data.user.id, email: data.user.email },
            data.accessToken,
          );
          return;
        }

        setVerificationEmail(email);
        setVerificationCode("");
        setPassword("");
        setConfirmPassword("");
        setMode("verify");
        setNotice(
          "Account created. Check your inbox for a verification code or link.",
        );
        return;
      }

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
          : mode === "register"
            ? "Registration failed. Try again."
            : "Sign in failed. Check your credentials.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleVerification(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setNotice(null);
    setIsSubmitting(true);

    try {
      const { data, error: authError } = await insforge.auth.verifyEmail({
        email: verificationEmail,
        otp: verificationCode,
      });

      if (authError || !data?.user || !data.accessToken) {
        throw authError ?? new Error("InsForge did not verify the account.");
      }

      onAuthenticated(
        { id: data.user.id, email: data.user.email },
        data.accessToken,
      );
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : "Verification failed. Check the code and try again.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleResendVerification() {
    setError(null);
    setNotice(null);
    setIsResending(true);

    try {
      const { error: authError } =
        await insforge.auth.resendVerificationEmail({
          email: verificationEmail,
        });

      if (authError) throw authError;
      setNotice("A new verification email has been sent.");
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : "Could not resend the verification email.",
      );
    } finally {
      setIsResending(false);
    }
  }

  const isRegistering = mode === "register";
  const isVerifying = mode === "verify";
  const title = isVerifying
    ? "Verify your email"
    : isRegistering
      ? "Create account"
      : "Sign in";
  const description = isVerifying
    ? `We sent verification instructions to ${verificationEmail}.`
    : isRegistering
      ? "Create your account to start investigating clusters."
      : "Use your InsForge account to access investigations and history.";

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

            {isVerifying ? (
              <EnvelopeSimple
                aria-hidden
                className="text-accent"
                size={24}
                weight="duotone"
              />
            ) : isRegistering ? (
              <UserPlus
                aria-hidden
                className="text-accent"
                size={24}
                weight="duotone"
              />
            ) : (
              <LockKey
                aria-hidden
                className="text-accent"
                size={24}
                weight="duotone"
              />
            )}

            <h2 className="mt-5 text-3xl font-semibold tracking-[-0.035em] text-ink">
              {title}
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-emerald-950/55">
              {description}
            </p>

            {!isVerifying ? (
              <div
                aria-label="Authentication mode"
                className="mt-7 grid grid-cols-2 rounded-xl bg-emerald-950/[0.055] p-1"
                role="group"
              >
                <button
                  aria-pressed={mode === "sign-in"}
                  className={`rounded-lg px-3 py-2 text-sm font-semibold transition ${
                    mode === "sign-in"
                      ? "bg-white text-ink shadow-sm"
                      : "text-emerald-950/55 hover:text-ink"
                  }`}
                  onClick={() => changeMode("sign-in")}
                  type="button"
                >
                  Sign in
                </button>
                <button
                  aria-pressed={mode === "register"}
                  className={`rounded-lg px-3 py-2 text-sm font-semibold transition ${
                    mode === "register"
                      ? "bg-white text-ink shadow-sm"
                      : "text-emerald-950/55 hover:text-ink"
                  }`}
                  onClick={() => changeMode("register")}
                  type="button"
                >
                  Create account
                </button>
              </div>
            ) : null}

            {isVerifying ? (
              <form className="mt-8 space-y-5" onSubmit={handleVerification}>
                <label className="block">
                  <span className="mb-2 block text-sm font-medium text-ink">
                    Verification code
                  </span>
                  <input
                    autoComplete="one-time-code"
                    className="w-full rounded-xl border border-emerald-950/15 bg-canvas/55 px-4 py-3 text-center font-mono text-lg tracking-[0.35em] text-ink outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/15"
                    inputMode="numeric"
                    maxLength={6}
                    onChange={(event) =>
                      setVerificationCode(event.target.value.replace(/\D/g, ""))
                    }
                    placeholder="000000"
                    required
                    type="text"
                    value={verificationCode}
                  />
                </label>

                {notice ? (
                  <p className="flex gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm leading-relaxed text-emerald-800" role="status">
                    <CheckCircle aria-hidden className="mt-0.5 shrink-0" size={17} />
                    {notice}
                  </p>
                ) : null}

                {error ? (
                  <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm leading-relaxed text-red-700" role="alert">
                    {error}
                  </p>
                ) : null}

                <button
                  className="flex w-full items-center justify-between rounded-xl bg-ink px-5 py-3.5 text-sm font-semibold text-white transition duration-300 ease-out hover:-translate-y-0.5 hover:bg-emerald-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-4 active:translate-y-px disabled:cursor-not-allowed disabled:opacity-60"
                  disabled={isSubmitting || verificationCode.length !== 6}
                  type="submit"
                >
                  <span>{isSubmitting ? "Verifying..." : "Verify account"}</span>
                  <ArrowRight aria-hidden size={17} weight="bold" />
                </button>

                <div className="flex items-center justify-between text-sm">
                  <button
                    className="font-medium text-emerald-800 transition hover:text-accent disabled:opacity-50"
                    disabled={isResending}
                    onClick={handleResendVerification}
                    type="button"
                  >
                    {isResending ? "Sending..." : "Resend email"}
                  </button>
                  <button
                    className="font-medium text-emerald-800 transition hover:text-accent"
                    onClick={() => {
                      setEmail(verificationEmail);
                      changeMode("sign-in");
                    }}
                    type="button"
                  >
                    Back to sign in
                  </button>
                </div>
              </form>
            ) : (
              <form className="mt-7 space-y-4" onSubmit={handleAuthSubmit}>
                {isRegistering ? (
                  <label className="block">
                    <span className="mb-2 block text-sm font-medium text-ink">
                      Name <span className="font-normal text-emerald-950/40">(optional)</span>
                    </span>
                    <input
                      autoComplete="name"
                      className="w-full rounded-xl border border-emerald-950/15 bg-canvas/55 px-4 py-3 text-sm text-ink outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/15"
                      onChange={(event) => setName(event.target.value)}
                      placeholder="Your name"
                      type="text"
                      value={name}
                    />
                  </label>
                ) : null}

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
                    autoComplete={isRegistering ? "new-password" : "current-password"}
                    className="w-full rounded-xl border border-emerald-950/15 bg-canvas/55 px-4 py-3 text-sm text-ink outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/15"
                    minLength={8}
                    onChange={(event) => setPassword(event.target.value)}
                    required
                    type="password"
                    value={password}
                  />
                </label>

                {isRegistering ? (
                  <label className="block">
                    <span className="mb-2 block text-sm font-medium text-ink">
                      Confirm password
                    </span>
                    <input
                      autoComplete="new-password"
                      className="w-full rounded-xl border border-emerald-950/15 bg-canvas/55 px-4 py-3 text-sm text-ink outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/15"
                      minLength={8}
                      onChange={(event) => setConfirmPassword(event.target.value)}
                      required
                      type="password"
                      value={confirmPassword}
                    />
                  </label>
                ) : null}

                {notice ? (
                  <p className="flex gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm leading-relaxed text-emerald-800" role="status">
                    <CheckCircle aria-hidden className="mt-0.5 shrink-0" size={17} />
                    {notice}
                  </p>
                ) : null}

                {error ? (
                  <div className="space-y-3">
                    <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm leading-relaxed text-red-700" role="alert">
                      {error}
                    </p>
                    {!isRegistering && error.toLowerCase().includes("verification") ? (
                      <button
                        className="text-sm font-semibold text-emerald-800 transition hover:text-accent"
                        onClick={() => {
                          setVerificationEmail(email);
                          setVerificationCode("");
                          setError(null);
                          setMode("verify");
                        }}
                        type="button"
                      >
                        Verify this email
                      </button>
                    ) : null}
                  </div>
                ) : null}

                <button
                  className="flex w-full items-center justify-between rounded-xl bg-ink px-5 py-3.5 text-sm font-semibold text-white transition duration-300 ease-out hover:-translate-y-0.5 hover:bg-emerald-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-4 active:translate-y-px disabled:cursor-not-allowed disabled:opacity-60"
                  disabled={isSubmitting}
                  type="submit"
                >
                  <span>
                    {isSubmitting
                      ? isRegistering
                        ? "Creating account..."
                        : "Signing in..."
                      : isRegistering
                        ? "Create account"
                        : "Sign in to dashboard"}
                  </span>
                  <ArrowRight aria-hidden size={17} weight="bold" />
                </button>
              </form>
            )}
          </div>
        </section>
      </div>
    </main>
  );
}
