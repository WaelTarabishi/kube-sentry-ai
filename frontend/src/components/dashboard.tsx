"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { SocketMessage } from "@insforge/sdk";
import {
  ArrowClockwise,
  Check,
  Clock,
  Copy,
  Cube,
  SignOut,
  SpinnerGap,
  WarningCircle,
} from "@phosphor-icons/react";

import { insforge } from "@/lib/insforge";
import {
  getInvestigationError,
  getRecentInvestigations,
  investigateCluster,
} from "@/services/investigations";
import type {
  Diagnosis,
  InvestigationHistory,
  ProgressState,
  ProgressStep,
  ProgressStepId,
} from "@/types/investigation";
import { INITIAL_PROGRESS } from "@/types/investigation";
import type { AuthUser } from "@/components/login-form";

interface DashboardProps {
  accessToken: string;
  user: AuthUser;
  onSignOut: () => Promise<void>;
}

interface ProgressMessage extends SocketMessage {
  requestId: string;
  step: ProgressStepId;
  state: ProgressState;
  status: InvestigationHistory["status"];
}

function newProgress(): ProgressStep[] {
  return INITIAL_PROGRESS.map((step) => ({ ...step }));
}

function applyProgress(
  current: ProgressStep[],
  stepId: ProgressStepId,
  state: ProgressState,
): ProgressStep[] {
  const activeIndex = current.findIndex((step) => step.id === stepId);
  if (activeIndex < 0) return current;

  return current.map((step, index) => ({
    ...step,
    state:
      index < activeIndex
        ? "completed"
        : index === activeIndex
          ? state
          : step.state === "failed"
            ? "pending"
            : step.state,
  }));
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function Dashboard({ accessToken, user, onSignOut }: DashboardProps) {
  const [diagnosis, setDiagnosis] = useState<Diagnosis | null>(null);
  const [progress, setProgress] = useState<ProgressStep[]>(newProgress);
  const [history, setHistory] = useState<InvestigationHistory[]>([]);
  const [isInvestigating, setIsInvestigating] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [realtimeWarning, setRealtimeWarning] = useState<string | null>(null);
  const activeRequestRef = useRef<string | null>(null);

  const loadHistory = useCallback(async () => {
    setHistoryError(null);
    try {
      setHistory(await getRecentInvestigations(user.id));
    } catch {
      setHistoryError("History is unavailable. Check the InsForge table setup.");
    } finally {
      setHistoryLoading(false);
    }
  }, [user.id]);

  useEffect(() => {
    void loadHistory();
  }, [loadHistory]);

  useEffect(() => {
    const channel = `investigation:${user.id}`;
    let disposed = false;

    function handleProgress(message: ProgressMessage) {
      if (message.requestId !== activeRequestRef.current) return;
      setProgress((current) => applyProgress(current, message.step, message.state));
    }

    async function subscribe() {
      insforge.realtime.on<ProgressMessage>(
        "investigation_progress",
        handleProgress,
      );
      try {
        await insforge.realtime.connect();
        const subscription = await insforge.realtime.subscribe(channel);
        if (!subscription.ok && !disposed) {
          setRealtimeWarning("Live progress is unavailable; the final result will still appear.");
        }
      } catch {
        if (!disposed) {
          setRealtimeWarning("Live progress is unavailable; the final result will still appear.");
        }
      }
    }

    void subscribe();
    return () => {
      disposed = true;
      insforge.realtime.off<ProgressMessage>(
        "investigation_progress",
        handleProgress,
      );
      insforge.realtime.unsubscribe(channel);
      insforge.realtime.disconnect();
    };
  }, [user.id]);

  async function handleInvestigate() {
    const requestId = crypto.randomUUID();
    activeRequestRef.current = requestId;
    setDiagnosis(null);
    setError(null);
    setProgress(
      newProgress().map((step, index) => ({
        ...step,
        state: index === 0 ? "active" : "pending",
      })),
    );
    setIsInvestigating(true);

    try {
      const result = await investigateCluster(accessToken, requestId);
      setDiagnosis(result.diagnosis);
      setProgress((current) =>
        current.map((step) => ({ ...step, state: "completed" })),
      );
      await loadHistory();
    } catch (caughtError) {
      setError(getInvestigationError(caughtError));
      setProgress((current) => {
        const activeIndex = current.findIndex((step) => step.state === "active");
        if (activeIndex < 0) return current;
        return current.map((step, index) =>
          index === activeIndex ? { ...step, state: "failed" } : step,
        );
      });
      await loadHistory();
    } finally {
      activeRequestRef.current = null;
      setIsInvestigating(false);
    }
  }

  return (
    <main className="min-h-[100dvh] px-4 py-5 sm:px-8 sm:py-8">
      <div className="mx-auto max-w-7xl overflow-hidden rounded-[2rem] border border-emerald-950/10 bg-white/85 shadow-[0_28px_90px_-58px_rgba(24,33,29,0.55)] backdrop-blur-sm">
        <header className="flex flex-col gap-4 border-b border-emerald-950/10 px-6 py-5 sm:flex-row sm:items-center sm:justify-between sm:px-9">
          <div className="flex items-center gap-3">
            <span className="grid h-9 w-9 place-items-center rounded-xl bg-ink text-white">
              <Cube aria-hidden size={19} weight="duotone" />
            </span>
            <div>
              <p className="text-sm font-semibold tracking-tight text-ink">
                AI Kubernetes Agent
              </p>
              <p className="mt-0.5 font-mono text-[10px] uppercase tracking-[0.15em] text-emerald-950/40">
                Investigation dashboard
              </p>
            </div>
          </div>
          <div className="flex items-center justify-between gap-4 sm:justify-end">
            <span className="max-w-48 truncate text-xs text-emerald-950/55">
              {user.email}
            </span>
            <button
              aria-label="Sign out"
              className="grid h-9 w-9 place-items-center rounded-lg border border-emerald-950/10 text-emerald-950/55 transition hover:border-emerald-950/20 hover:text-ink active:translate-y-px"
              onClick={() => void onSignOut()}
              type="button"
            >
              <SignOut aria-hidden size={17} />
            </button>
          </div>
        </header>

        <div className="grid lg:grid-cols-[minmax(0,1.35fr)_minmax(19rem,0.65fr)]">
          <section className="px-6 py-8 sm:px-9 sm:py-10 lg:border-r lg:border-emerald-950/10">
            <div className="flex flex-col gap-6 border-b border-emerald-950/10 pb-8 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-accent">
                  Cluster diagnostics
                </p>
                <h1 className="mt-3 text-3xl font-semibold tracking-[-0.04em] text-ink sm:text-4xl">
                  Investigate the cluster
                </h1>
                <p className="mt-3 max-w-xl text-sm leading-relaxed text-emerald-950/55">
                  Collect live evidence, run AI reasoning, and receive a practical fix.
                </p>
              </div>
              <button
                className="inline-flex shrink-0 items-center justify-center gap-2 rounded-xl bg-ink px-5 py-3.5 text-sm font-semibold text-white transition duration-300 ease-out hover:-translate-y-0.5 hover:bg-emerald-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-4 active:translate-y-px disabled:cursor-not-allowed disabled:opacity-60"
                disabled={isInvestigating}
                onClick={() => void handleInvestigate()}
                type="button"
              >
                {isInvestigating ? (
                  <SpinnerGap aria-hidden className="animate-spin motion-reduce:animate-none" size={17} />
                ) : (
                  <ArrowClockwise aria-hidden size={17} weight="bold" />
                )}
                {isInvestigating ? "Investigating..." : "Investigate Cluster"}
              </button>
            </div>

            <section className="py-8" aria-labelledby="progress-heading">
              <div className="flex items-center justify-between">
                <h2 id="progress-heading" className="text-sm font-semibold text-ink">
                  Investigation status
                </h2>
                {isInvestigating ? (
                  <span className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.14em] text-accent">
                    <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-accent motion-reduce:animate-none" />
                    Live
                  </span>
                ) : null}
              </div>

              {realtimeWarning ? (
                <p className="mt-4 text-xs leading-relaxed text-amber-700">
                  {realtimeWarning}
                </p>
              ) : null}

              <ol className="mt-5 grid gap-x-8 gap-y-1 sm:grid-cols-2">
                {progress.map((step) => (
                  <li
                    className="flex items-center gap-3 border-b border-emerald-950/8 py-3"
                    key={step.id}
                  >
                    <ProgressIcon state={step.state} />
                    <span
                      className={`text-sm ${
                        step.state === "pending"
                          ? "text-emerald-950/35"
                          : step.state === "failed"
                            ? "text-red-700"
                            : "text-ink/80"
                      }`}
                    >
                      {step.label}
                    </span>
                  </li>
                ))}
              </ol>
            </section>

            {error ? (
              <div className="mb-8 flex gap-3 rounded-2xl border border-red-200 bg-red-50 px-4 py-4 text-sm leading-relaxed text-red-700" role="alert">
                <WarningCircle aria-hidden className="mt-0.5 shrink-0" size={18} />
                <p>{error}</p>
              </div>
            ) : null}

            <DiagnosisPanel diagnosis={diagnosis} isLoading={isInvestigating} />
          </section>

          <HistoryPanel
            error={historyError}
            history={history}
            isLoading={historyLoading}
            onRetry={() => void loadHistory()}
          />
        </div>
      </div>
    </main>
  );
}

function ProgressIcon({ state }: { state: ProgressState }) {
  const classes =
    "grid h-5 w-5 shrink-0 place-items-center rounded-full border";
  if (state === "completed") {
    return (
      <span className={`${classes} border-accent bg-accent text-white`}>
        <Check aria-hidden size={11} weight="bold" />
      </span>
    );
  }
  if (state === "active") {
    return (
      <span className={`${classes} border-accent/40 bg-accent/10 text-accent`}>
        <SpinnerGap aria-hidden className="animate-spin motion-reduce:animate-none" size={11} />
      </span>
    );
  }
  if (state === "failed") {
    return (
      <span className={`${classes} border-red-300 bg-red-50 text-red-600`}>
        <WarningCircle aria-hidden size={11} weight="fill" />
      </span>
    );
  }
  return <span className={`${classes} border-emerald-950/15 bg-canvas`} />;
}

function DiagnosisPanel({
  diagnosis,
  isLoading,
}: {
  diagnosis: Diagnosis | null;
  isLoading: boolean;
}) {
  const [copied, setCopied] = useState<string | null>(null);

  async function copyCommand(command: string) {
    await navigator.clipboard.writeText(command);
    setCopied(command);
    window.setTimeout(() => setCopied(null), 1600);
  }

  if (isLoading) {
    return (
      <section aria-label="Diagnosis loading" className="border-t border-emerald-950/10 pt-8">
        <div className="h-3 w-24 animate-pulse rounded bg-emerald-950/10 motion-reduce:animate-none" />
        <div className="mt-5 h-7 w-2/3 animate-pulse rounded bg-emerald-950/10 motion-reduce:animate-none" />
        <div className="mt-4 h-3 w-full animate-pulse rounded bg-emerald-950/10 motion-reduce:animate-none" />
        <div className="mt-2 h-3 w-4/5 animate-pulse rounded bg-emerald-950/10 motion-reduce:animate-none" />
      </section>
    );
  }

  if (!diagnosis) {
    return (
      <section className="border-t border-emerald-950/10 py-10 text-center">
        <span className="mx-auto grid h-10 w-10 place-items-center rounded-xl bg-emerald-950/5 text-emerald-950/35">
          <Cube aria-hidden size={20} weight="duotone" />
        </span>
        <h2 className="mt-4 text-sm font-semibold text-ink">No diagnosis yet</h2>
        <p className="mx-auto mt-2 max-w-sm text-sm leading-relaxed text-emerald-950/45">
          Start an investigation to collect evidence and identify the root cause.
        </p>
      </section>
    );
  }

  return (
    <section className="border-t border-emerald-950/10 pt-8" aria-labelledby="diagnosis-heading">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-accent">
            Root cause
          </p>
          <h2 id="diagnosis-heading" className="mt-2 text-2xl font-semibold tracking-[-0.03em] text-ink">
            {diagnosis.root_cause}
          </h2>
        </div>
        <div className="shrink-0 rounded-xl border border-accent/20 bg-accent/5 px-4 py-2 text-right">
          <p className="font-mono text-[9px] uppercase tracking-[0.14em] text-accent/70">
            Confidence
          </p>
          <p className="mt-0.5 font-mono text-xl font-semibold text-accent">
            {diagnosis.confidence}%
          </p>
        </div>
      </div>

      <div className="mt-7 grid gap-6 sm:grid-cols-2">
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-[0.1em] text-emerald-950/45">
            Explanation
          </h3>
          <p className="mt-2 text-sm leading-relaxed text-emerald-950/65">
            {diagnosis.explanation}
          </p>
        </div>
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-[0.1em] text-emerald-950/45">
            Suggested fix
          </h3>
          <p className="mt-2 text-sm leading-relaxed text-emerald-950/65">
            {diagnosis.fix}
          </p>
        </div>
      </div>

      <div className="mt-7">
        <h3 className="text-xs font-semibold uppercase tracking-[0.1em] text-emerald-950/45">
          kubectl command
        </h3>
        <div className="mt-2 space-y-2">
          {diagnosis.kubectl_commands.map((command) => (
            <div className="flex items-start gap-3 rounded-xl bg-ink px-4 py-3 text-emerald-50" key={command}>
              <code className="min-w-0 flex-1 overflow-x-auto font-mono text-xs leading-relaxed">
                {command}
              </code>
              <button
                aria-label="Copy kubectl command"
                className="shrink-0 text-emerald-50/55 transition hover:text-white active:translate-y-px"
                onClick={() => void copyCommand(command)}
                type="button"
              >
                {copied === command ? (
                  <Check aria-hidden size={16} weight="bold" />
                ) : (
                  <Copy aria-hidden size={16} />
                )}
              </button>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function HistoryPanel({
  history,
  isLoading,
  error,
  onRetry,
}: {
  history: InvestigationHistory[];
  isLoading: boolean;
  error: string | null;
  onRetry: () => void;
}) {
  return (
    <aside className="bg-[#f0f4f1] px-6 py-8 sm:px-9 sm:py-10">
      <div className="flex items-center justify-between">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-accent">
            History
          </p>
          <h2 className="mt-2 text-lg font-semibold tracking-tight text-ink">
            Recent investigations
          </h2>
        </div>
        <button
          aria-label="Refresh investigation history"
          className="grid h-9 w-9 place-items-center rounded-lg border border-emerald-950/10 bg-white/60 text-emerald-950/55 transition hover:text-ink active:translate-y-px"
          onClick={onRetry}
          type="button"
        >
          <ArrowClockwise aria-hidden size={15} />
        </button>
      </div>

      {isLoading ? (
        <div className="mt-7 space-y-4" aria-label="History loading">
          {[0, 1, 2].map((item) => (
            <div className="border-b border-emerald-950/10 pb-4" key={item}>
              <div className="h-3 w-2/3 animate-pulse rounded bg-emerald-950/10 motion-reduce:animate-none" />
              <div className="mt-3 h-2 w-1/2 animate-pulse rounded bg-emerald-950/10 motion-reduce:animate-none" />
            </div>
          ))}
        </div>
      ) : error ? (
        <div className="mt-7 rounded-xl border border-amber-200 bg-amber-50 px-4 py-4 text-sm leading-relaxed text-amber-800">
          {error}
        </div>
      ) : history.length === 0 ? (
        <div className="mt-8 border-t border-emerald-950/10 pt-8 text-center">
          <Clock aria-hidden className="mx-auto text-emerald-950/30" size={22} />
          <p className="mt-3 text-sm font-medium text-ink">No previous investigations</p>
          <p className="mt-1 text-xs leading-relaxed text-emerald-950/45">
            Completed runs will appear here.
          </p>
        </div>
      ) : (
        <div className="mt-7 overflow-hidden rounded-xl border border-emerald-950/10 bg-white/55">
          <table className="w-full table-fixed text-left">
            <thead>
              <tr className="border-b border-emerald-950/10 font-mono text-[9px] uppercase tracking-[0.12em] text-emerald-950/40">
                <th className="w-[56%] px-3 py-3 font-medium">Root cause</th>
                <th className="w-[22%] px-2 py-3 font-medium">Score</th>
                <th className="w-[22%] px-2 py-3 font-medium">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-emerald-950/8">
              {history.map((item) => (
                <tr key={item.id}>
                  <td className="px-3 py-3 align-top">
                    <p className="truncate text-xs font-medium text-ink/80">
                      {item.root_cause ?? "Investigation in progress"}
                    </p>
                    <p className="mt-1 font-mono text-[9px] text-emerald-950/40">
                      {formatDate(item.created_at)} · {item.namespace}
                    </p>
                  </td>
                  <td className="px-2 py-3 align-top font-mono text-xs text-emerald-950/60">
                    {item.confidence === null ? "—" : `${item.confidence}%`}
                  </td>
                  <td className="px-2 py-3 align-top">
                    <span
                      className={`inline-block h-2 w-2 rounded-full ${
                        item.status === "success"
                          ? "bg-accent"
                          : item.status === "failed"
                            ? "bg-red-500"
                            : "animate-pulse bg-amber-500 motion-reduce:animate-none"
                      }`}
                      title={item.status}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </aside>
  );
}
