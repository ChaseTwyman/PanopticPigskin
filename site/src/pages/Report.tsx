import { useEffect, useRef, useState } from "react";
import { buttonClass } from "../components/ButtonLink";
import { ArrowUpRight, CheckIcon } from "../components/Icons";
import { REPORT_STAGES } from "../content";
import { frameDocument, isAppShell, retargetLinks } from "../lib/frames";
import { prefersReducedMotion } from "../lib/motion";
import { useTheme } from "../lib/theme";
import { useDocumentTitle } from "../lib/useDocumentTitle";

const REPORT = "/embed/report/index.html";

// Four stages plus a closing beat: about 2.5 s in all. The report itself was
// computed ahead of time; the sequence only paces its arrival.
const STAGE_MS = 600;
const FINAL_BEAT_MS = 100;

type Phase = { kind: "idle" } | { kind: "running"; step: number } | { kind: "done" };
type StageState = "done" | "active" | "pending";

export default function Report() {
  useDocumentTitle("Player report · PanopticPigskin");
  const [phase, setPhase] = useState<Phase>({ kind: "idle" });
  const timers = useRef<number[]>([]);
  const heading = useRef<HTMLHeadingElement>(null);
  const reportSection = useRef<HTMLElement>(null);
  const revealed = useRef(false);

  useEffect(() => {
    const pending = timers.current;
    return () => pending.forEach((id) => window.clearTimeout(id));
  }, []);

  const generate = () => {
    if (phase.kind !== "idle") return;
    if (prefersReducedMotion()) {
      setPhase({ kind: "done" });
      return;
    }
    setPhase({ kind: "running", step: 0 });
    for (let i = 1; i < REPORT_STAGES.length; i++) {
      timers.current.push(window.setTimeout(() => setPhase({ kind: "running", step: i }), i * STAGE_MS));
    }
    timers.current.push(
      window.setTimeout(() => setPhase({ kind: "done" }), REPORT_STAGES.length * STAGE_MS + FINAL_BEAT_MS),
    );
  };

  // When the report arrives, take the view and keyboard focus to it.
  useEffect(() => {
    if (phase.kind !== "done" || revealed.current) return;
    revealed.current = true;
    reportSection.current?.scrollIntoView({ behavior: prefersReducedMotion() ? "instant" : "smooth", block: "start" });
    heading.current?.focus({ preventScroll: true });
  }, [phase.kind]);

  const started = phase.kind !== "idle";
  const done = phase.kind === "done";
  const step = phase.kind === "running" ? phase.step : done ? REPORT_STAGES.length : 0;
  const progress = done ? 100 : started ? ((step + 1) / REPORT_STAGES.length) * 100 : 0;
  const announcement =
    phase.kind === "running" ? `${REPORT_STAGES[phase.step]}…` : done ? "Report ready." : "";

  const stageState = (i: number): StageState => {
    if (done || i < step) return "done";
    if (phase.kind === "running" && i === step) return "active";
    return "pending";
  };

  return (
    <>
      <section aria-labelledby="report-hero-title" className="relative isolate overflow-hidden border-b border-line">
        <div aria-hidden="true" className="pointer-events-none absolute inset-0 -z-10">
          <div className="field-lines hero-field absolute inset-0" />
          <div className="hero-glow absolute inset-0" />
        </div>

        <div className="mx-auto max-w-4xl px-4 pb-16 pt-14 text-center sm:px-6 sm:pb-20 sm:pt-20">
          <p className="font-mono text-xs font-medium uppercase tracking-[0.18em] text-turf">Player report · Play 001</p>
          <h1
            id="report-hero-title"
            className="mx-auto mt-4 max-w-4xl font-display text-[clamp(2.6rem,8vw,5.25rem)] font-extrabold uppercase leading-[0.9]"
          >
            Every player, <span className="text-turf">graded from the tracking.</span>
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-lg leading-relaxed text-ink-2 sm:text-xl">
            Separation at the throw, pressure in the pocket and a grade for each of the 22 players on Ravens at Chiefs,
            2024 Week 1: Mahomes to Noah Gray for 9.7 yards.
          </p>

          <div className="mt-8 flex flex-col items-center gap-4">
            <button
              type="button"
              onClick={generate}
              aria-disabled={started}
              className={buttonClass(
                "primary",
                `w-full sm:w-auto sm:min-w-64 ${started ? "cursor-default opacity-80 hover:bg-turf" : ""}`,
              )}
            >
              {done ? (
                <>
                  <CheckIcon className="h-5 w-5" />
                  Report ready
                </>
              ) : started ? (
                "Generating…"
              ) : (
                "Generate report"
              )}
            </button>
            <p className="max-w-md text-sm text-ink-3">
              Pre-computed, not generated on the spot: every number was measured from the tracking ahead of time, and
              the button assembles the view from files already on this site.
            </p>
          </div>

          {started ? (
            <div className="mx-auto mt-10 w-full max-w-md rounded-2xl border border-line bg-surface p-5 text-left shadow-card">
              <div className="h-1.5 overflow-hidden rounded-full bg-line" aria-hidden="true">
                <div
                  className="h-full rounded-full bg-turf transition-[width] duration-500 ease-out"
                  style={{ width: `${progress}%` }}
                />
              </div>
              <ol className="mt-5 space-y-3">
                {REPORT_STAGES.map((stage, i) => {
                  const state = stageState(i);
                  return (
                    <li key={stage} className="flex items-center gap-3">
                      <StageMark state={state} />
                      <span className={state === "pending" ? "text-ink-3" : "text-ink"}>{stage}</span>
                      <span className="sr-only">
                        {state === "done" ? "(done)" : state === "active" ? "(in progress)" : "(waiting)"}
                      </span>
                    </li>
                  );
                })}
              </ol>
            </div>
          ) : null}

          <p role="status" aria-live="polite" className="sr-only">
            {announcement}
          </p>
        </div>
      </section>

      {started ? (
        <section
          id="report"
          ref={reportSection}
          aria-labelledby="report-title"
          inert={!done}
          className={done ? "pb-20 pt-10 sm:pb-24 sm:pt-14" : "h-0 overflow-hidden"}
        >
          <div className="mx-auto max-w-6xl px-4 sm:px-6">
            <div className="flex flex-wrap items-end justify-between gap-x-6 gap-y-3 border-b border-line pb-4">
              <div>
                <p className="font-mono text-xs font-medium uppercase tracking-[0.18em] text-turf">
                  Pre-computed from the tracking
                </p>
                <h2
                  id="report-title"
                  ref={heading}
                  tabIndex={-1}
                  className="mt-2 rounded-md font-display text-4xl font-bold uppercase leading-none sm:text-5xl"
                >
                  The report
                </h2>
              </div>
              <a
                href={REPORT}
                target="_blank"
                rel="noopener"
                className="inline-flex items-center gap-1 rounded-md py-1 font-display text-base font-semibold uppercase tracking-[0.06em] text-turf hover:underline hover:underline-offset-4"
              >
                Open report in its own tab
                <ArrowUpRight className="h-4 w-4" />
                <span className="sr-only">(opens in a new tab)</span>
              </a>
            </div>
            <ReportFrame />
          </div>
        </section>
      ) : null}
    </>
  );
}

function StageMark({ state }: { state: StageState }) {
  if (state === "done") {
    return (
      <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-turf text-on-turf">
        <CheckIcon className="h-3.5 w-3.5" />
      </span>
    );
  }
  if (state === "active") {
    return <span className="h-6 w-6 shrink-0 animate-spin rounded-full border-2 border-line-2 border-t-turf" />;
  }
  return <span className="h-6 w-6 shrink-0 rounded-full border-2 border-line-2" />;
}

type FrameStatus = "loading" | "ready" | "missing";

/**
 * The static report in a same-origin frame, sized to its content so the page
 * scrolls as one. If the frame's document cannot be read, it keeps a tall
 * fixed height and scrolls on its own.
 */
function ReportFrame() {
  const { theme } = useTheme();
  const frame = useRef<HTMLIFrameElement>(null);
  const stopWatching = useRef<(() => void) | null>(null);
  const [height, setHeight] = useState<number | null>(null);
  const [status, setStatus] = useState<FrameStatus>("loading");

  useEffect(() => () => stopWatching.current?.(), []);

  // The report's stylesheet reads data-theme on its root, so it follows the site's toggle.
  useEffect(() => {
    if (status !== "ready") return;
    frameDocument(frame.current)?.documentElement.setAttribute("data-theme", theme);
  }, [theme, status]);

  const onLoad = () => {
    stopWatching.current?.();
    stopWatching.current = null;
    const el = frame.current;
    const doc = frameDocument(el);
    const win = el?.contentWindow ?? null;
    if (!doc || !win) {
      setStatus("ready");
      return;
    }
    if (isAppShell(doc)) {
      setStatus("missing");
      return;
    }
    doc.documentElement.setAttribute("data-theme", theme);
    retargetLinks(doc);

    let observer: ResizeObserver | null = null;
    let last = 0;
    const recent: number[] = [];
    const measure = () => {
      const root = doc.documentElement;
      // A horizontal scrollbar on the frame's root would eat into the height.
      const scrollbar = Math.max(0, win.innerHeight - root.clientHeight);
      const next = Math.ceil(root.getBoundingClientRect().height) + scrollbar;
      if (next <= 0 || Math.abs(next - last) < 2) return;
      // A page sized from its own viewport (vh units) would grow with every
      // resize. After a burst of changes, stop syncing and fall back to the
      // fixed height with its own scroll.
      const now = performance.now();
      recent.push(now);
      while (recent.length > 0 && now - (recent[0] ?? now) > 1000) recent.shift();
      if (recent.length > 12) {
        observer?.disconnect();
        setHeight(null);
        return;
      }
      last = next;
      setHeight(next);
    };
    measure();

    // The frame's own ResizeObserver sees its layout (fonts arriving, width changes).
    const FrameObserver = (win as Window & typeof globalThis).ResizeObserver ?? window.ResizeObserver;
    observer = FrameObserver ? new FrameObserver(measure) : null;
    observer?.observe(doc.documentElement);
    doc.fonts?.ready.then(measure).catch(() => {});
    stopWatching.current = () => observer?.disconnect();
    setStatus("ready");
  };

  return (
    <div className="relative mt-6 overflow-hidden rounded-2xl border border-line-2 bg-surface shadow-card">
      {status === "missing" ? (
        <div className="grid min-h-80 place-items-center p-8 text-center">
          <div>
            <p className="font-display text-2xl font-bold uppercase tracking-[0.04em]">The report is not published here yet</p>
            <p className="mt-2 font-mono text-xs text-ink-3">{REPORT}</p>
          </div>
        </div>
      ) : (
        <iframe
          ref={frame}
          src={REPORT}
          title="Play 001 report: grades and measurements for every player, from the tracking"
          onLoad={onLoad}
          className={`block w-full border-0 ${height === null ? "h-[85vh]" : ""}`}
          style={height === null ? undefined : { height: `${height}px` }}
        />
      )}
    </div>
  );
}
