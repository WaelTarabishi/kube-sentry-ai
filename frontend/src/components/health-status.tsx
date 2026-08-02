"use client";

import { useHealth } from "@/hooks/use-health";

export function HealthStatus() {
  const { data, isError, isLoading, isFetching, refetch } = useHealth();

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-sm text-emerald-950/60" role="status">
        <span className="h-2 w-2 animate-pulse rounded-full bg-amber-500 motion-reduce:animate-none" />
        System Status: Checking
      </div>
    );
  }

  if (isError || data?.status !== "healthy") {
    return (
      <div className="flex items-center gap-3 text-sm text-red-800" role="status">
        <span className="h-2 w-2 rounded-full bg-red-600" />
        <span>System Status: Unavailable</span>
        <button
          type="button"
          onClick={() => refetch()}
          disabled={isFetching}
          className="font-semibold underline decoration-red-800/30 underline-offset-4 disabled:opacity-50"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2 text-sm text-emerald-950/65" role="status">
      <span className="h-2 w-2 rounded-full bg-accent shadow-[0_0_0_4px_rgba(47,118,88,0.12)]" />
      System Status: Ready
    </div>
  );
}

