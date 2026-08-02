"use client";

import { useEffect, useState } from "react";
import { Cube } from "@phosphor-icons/react";

import { Dashboard } from "@/components/dashboard";
import { AuthUser, LoginForm } from "@/components/login-form";
import { insforge } from "@/lib/insforge";

interface Session {
  accessToken: string;
  user: AuthUser;
}

export function AgentApplication() {
  const [session, setSession] = useState<Session | null>(null);
  const [isRestoring, setIsRestoring] = useState(true);

  useEffect(() => {
    let disposed = false;

    async function restoreSession() {
      try {
        const { data, error } = await insforge.auth.refreshSession();
        if (!disposed && !error && data?.user && data.accessToken) {
          setSession({
            accessToken: data.accessToken,
            user: { id: data.user.id, email: data.user.email },
          });
        }
      } finally {
        if (!disposed) setIsRestoring(false);
      }
    }

    void restoreSession();
    return () => {
      disposed = true;
    };
  }, []);

  async function handleSignOut() {
    await insforge.auth.signOut();
    setSession(null);
  }

  if (isRestoring) {
    return (
      <main className="grid min-h-[100dvh] place-items-center px-4">
        <div className="text-center">
          <span className="mx-auto grid h-11 w-11 animate-pulse place-items-center rounded-xl bg-ink text-white motion-reduce:animate-none">
            <Cube aria-hidden size={21} weight="duotone" />
          </span>
          <p className="mt-4 text-sm text-emerald-950/50">Restoring session...</p>
        </div>
      </main>
    );
  }

  if (!session) {
    return (
      <LoginForm
        onAuthenticated={(user, accessToken) =>
          setSession({ user, accessToken })
        }
      />
    );
  }

  return (
    <Dashboard
      accessToken={session.accessToken}
      onSignOut={handleSignOut}
      user={session.user}
    />
  );
}
