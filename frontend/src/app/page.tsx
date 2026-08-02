import { HealthStatus } from "@/components/health-status";

export default function Home() {
  return (
    <main className="min-h-[100dvh] overflow-hidden px-4 py-6 sm:px-8 sm:py-8">
      <div className="mx-auto flex min-h-[calc(100dvh-3rem)] max-w-7xl flex-col rounded-[2rem] border border-emerald-950/10 bg-white/70 shadow-[0_24px_80px_-48px_rgba(24,33,29,0.45)] sm:min-h-[calc(100dvh-4rem)]">
        <header className="flex items-center justify-between border-b border-emerald-950/10 px-6 py-5 sm:px-10">
          <div className="flex items-center gap-3">
            <span className="grid h-8 w-8 place-items-center rounded-lg bg-ink" aria-hidden="true">
              <span className="h-2.5 w-2.5 rounded-sm border border-emerald-100/80" />
            </span>
            <span className="text-sm font-semibold tracking-tight text-ink">
              AI Kubernetes Agent
            </span>
          </div>
          <span className="hidden font-mono text-[11px] uppercase tracking-[0.18em] text-emerald-950/45 sm:block">
            On-demand diagnostics
          </span>
        </header>

        <section className="grid flex-1 items-stretch md:grid-cols-[1.15fr_0.85fr]">
          <div className="flex flex-col justify-center px-6 py-14 sm:px-10 md:px-14 md:py-20 lg:px-20">
            <p className="mb-6 font-mono text-xs font-medium uppercase tracking-[0.2em] text-accent">
              Cluster investigation workspace
            </p>
            <h1 className="max-w-2xl text-4xl font-semibold leading-[0.98] tracking-[-0.045em] text-ink sm:text-5xl md:text-6xl">
              Troubleshoot Kubernetes with AI
            </h1>
            <p className="mt-7 max-w-[58ch] text-base leading-relaxed text-emerald-950/60">
              Start an on-demand investigation, review the evidence, and turn cluster signals into a clear diagnosis.
            </p>

            <div className="mt-10 flex flex-col items-start gap-5 sm:flex-row sm:items-center">
              <button
                type="button"
                aria-describedby="investigation-note"
                className="rounded-xl bg-ink px-6 py-3.5 text-sm font-semibold text-white shadow-[0_12px_28px_-16px_rgba(24,33,29,0.75)] transition duration-300 ease-out hover:-translate-y-0.5 hover:bg-emerald-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-4 active:translate-y-px"
              >
                Investigate Cluster
              </button>
              <HealthStatus />
            </div>
            <p id="investigation-note" className="mt-4 text-xs leading-relaxed text-emerald-950/45">
              Investigation workflow will be connected in the next implementation phase.
            </p>
          </div>

          <div className="relative min-h-80 overflow-hidden border-t border-emerald-950/10 bg-[#e8eee9] p-6 sm:p-10 md:min-h-full md:border-l md:border-t-0">
            <div className="absolute -right-24 -top-24 h-72 w-72 rounded-full border border-accent/15" />
            <div className="absolute -right-8 -top-8 h-40 w-40 rounded-full border border-accent/20" />
            <div className="relative flex h-full min-h-72 flex-col justify-between rounded-[1.5rem] border border-white/70 bg-white/55 p-6 shadow-[inset_0_1px_0_rgba(255,255,255,0.8)] backdrop-blur-sm sm:p-8">
              <div className="flex items-center justify-between">
                <span className="font-mono text-[11px] uppercase tracking-[0.16em] text-emerald-950/50">
                  Investigation pipeline
                </span>
                <span className="h-2 w-2 animate-pulse rounded-full bg-accent motion-reduce:animate-none" />
              </div>

              <div className="my-10 space-y-3">
                {["Request received", "Cluster evidence", "Root cause analysis"].map((label, index) => (
                  <div key={label} className="flex items-center gap-4 border-b border-emerald-950/10 pb-3">
                    <span className="font-mono text-xs text-accent">0{index + 1}</span>
                    <span className="text-sm font-medium text-ink/75">{label}</span>
                  </div>
                ))}
              </div>

              <p className="max-w-xs text-sm leading-relaxed text-emerald-950/55">
                The foundation is ready. Kubernetes collection and AI reasoning remain intentionally disconnected.
              </p>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}

