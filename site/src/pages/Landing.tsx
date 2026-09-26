import { Link } from "react-router-dom";
import { ButtonLink } from "../components/ButtonLink";
import { ArrowRight, FeatureIcon, PlusIcon } from "../components/Icons";
import { MediaSlot } from "../components/MediaSlot";
import { SectionHeading } from "../components/SectionHeading";
import { ANGLES, CLIP, FAQS, FEATURES, MOMENTS, STATS, STEPS } from "../content";
import { useDocumentTitle } from "../lib/useDocumentTitle";

export default function Landing() {
  useDocumentTitle("PanopticPigskin: one NFL play, rebuilt in 3D");
  return (
    <>
      <Hero />
      <Features />
      <Angles />
      <Moments />
      <HowItWorks />
      <Numbers />
      <Faq />
      <ClosingCall />
    </>
  );
}

function Hero() {
  return (
    <section aria-labelledby="hero-title" className="relative isolate overflow-hidden">
      <div aria-hidden="true" className="pointer-events-none absolute inset-0 -z-10">
        <div className="field-lines hero-field absolute inset-0" />
        <div className="hero-glow absolute inset-0" />
      </div>

      <div className="mx-auto max-w-6xl px-4 pb-12 pt-14 text-center sm:px-6 sm:pt-20 lg:pt-24">
        <p className="inline-flex items-center gap-2 rounded-full border border-line-2 bg-surface/80 px-3 py-1.5 font-mono text-[0.68rem] font-medium uppercase tracking-[0.16em] text-ink-2 backdrop-blur-sm">
          <span className="h-1.5 w-1.5 rounded-full bg-turf" aria-hidden="true" />
          Research demo · one play in 3D
        </p>

        <h1
          id="hero-title"
          className="mx-auto mt-6 max-w-5xl font-display text-[clamp(2.75rem,9vw,6.25rem)] font-extrabold uppercase leading-[0.88] tracking-[-0.005em]"
        >
          Two camera angles in. <span className="text-turf">Every angle out.</span>
        </h1>

        <p className="mx-auto mt-6 max-w-2xl text-lg leading-relaxed text-ink-2 sm:text-xl">
          PanopticPigskin turns the two broadcast <span className="whitespace-nowrap">All-22</span> clips of one NFL play
          into a 3D replay: every player placed on a calibrated field frame by frame, posed as a full human body fitted to
          both cameras, and viewable from any angle.
        </p>

        <div className="mt-8 flex flex-col items-stretch justify-center gap-3 sm:flex-row sm:items-center">
          <ButtonLink to="/playground">
            Open the playground
            <ArrowRight className="h-5 w-5" />
          </ButtonLink>
          <ButtonLink to="/report" variant="secondary">
            Generate the report
          </ButtonLink>
        </div>
      </div>

      <div className="mx-auto max-w-5xl px-4 pb-16 sm:px-6 sm:pb-24">
        <figure className="shadow-hero rounded-2xl border border-line-2 bg-screen p-1.5 sm:p-2">
          <div className="flex items-center justify-between gap-3 px-2 pb-2 pt-1 font-mono text-[0.65rem] uppercase tracking-[0.16em] text-screen-dim sm:text-[0.7rem]">
            <span className="flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-flag" aria-hidden="true" />
              Angle 1 · Follow cam
            </span>
            <span className="hidden sm:inline">Rendered from the reconstruction</span>
          </div>
          <MediaSlot
            src="/media/follow.mp4"
            poster="/media/poster.jpg"
            label="Follow cam"
            description="The reconstructed play, rendered with a camera that follows the action."
            eager
          />
          <figcaption className="mt-1.5 grid grid-cols-2 gap-px overflow-hidden rounded-lg bg-screen-line font-mono text-[0.68rem] uppercase tracking-[0.12em] sm:grid-cols-4">
            <ScoreCell label="Game" value="BAL at KC" />
            <ScoreCell label="Season" value="2024 · Week 1" />
            <ScoreCell label="Play" value="Mahomes to Gray" />
            <ScoreCell label="Result" value="Complete, 9.7 yd" />
          </figcaption>
        </figure>
      </div>
    </section>
  );
}

function ScoreCell({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-screen px-3 py-2.5">
      <span className="block text-screen-dim">{label}</span>
      <span className="mt-0.5 block font-medium text-screen-ink">{value}</span>
    </div>
  );
}

function Features() {
  return (
    <section aria-labelledby="features-title" className="border-t border-line bg-bg-2 py-20 sm:py-24">
      <div className="mx-auto max-w-6xl px-4 sm:px-6">
        <SectionHeading
          id="features-title"
          eyebrow="What you get"
          title="A play you can walk around in"
          intro="A 3D model of the play, rebuilt from the two broadcast clips: move the camera anywhere, stop on any frame, and read the numbers off the tracking."
        />
        <ul className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((feature) => (
            <li
              key={feature.title}
              className="flex flex-col rounded-2xl border border-line bg-surface p-6 shadow-card"
            >
              <span className="inline-flex h-11 w-11 items-center justify-center rounded-xl bg-turf-soft text-turf">
                <FeatureIcon name={feature.icon} className="h-6 w-6" />
              </span>
              <h3 className="mt-5 font-display text-2xl font-bold uppercase leading-tight tracking-[0.01em]">
                {feature.title}
              </h3>
              <p className="mt-2 text-ink-2">{feature.body}</p>
              {feature.link ? (
                <Link
                  to={feature.link.to}
                  className="mt-auto inline-flex items-center gap-1.5 self-start pt-4 font-display text-base font-semibold uppercase tracking-[0.06em] text-turf hover:underline hover:underline-offset-4"
                >
                  {feature.link.label}
                  <ArrowRight className="h-4 w-4" />
                </Link>
              ) : null}
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

function Angles() {
  return (
    <section id="angles" aria-labelledby="angles-title" className="py-20 sm:py-24">
      <div className="mx-auto max-w-6xl px-4 sm:px-6">
        <SectionHeading
          id="angles-title"
          eyebrow="Three angles"
          title="One play, any camera"
          intro="The clip at the top follows the action. Because the reconstruction is 3D, the same play can be filmed from anywhere, including exactly where a broadcast camera stood."
        />
        <div className="mt-12 grid gap-10 md:grid-cols-2 md:gap-6">
          {ANGLES.map((angle) => (
            <figure key={angle.src}>
              <div className="shadow-hero rounded-2xl border border-line-2 bg-screen p-1.5">
                <MediaSlot src={angle.src} label={angle.name} description={`${angle.name}: ${angle.body}`} />
              </div>
              <figcaption className="mt-5 px-1">
                <p className="font-mono text-xs font-medium uppercase tracking-[0.16em] text-turf">
                  Angle {angle.n} · {angle.name}
                </p>
                <h3 className="mt-2 font-display text-2xl font-bold uppercase leading-tight sm:text-[1.75rem]">
                  {angle.title}
                </h3>
                <p className="mt-2 text-ink-2">{angle.body}</p>
              </figcaption>
            </figure>
          ))}
        </div>
      </div>
    </section>
  );
}

function clipPercent(frame: number): number {
  return ((frame - CLIP.first) / (CLIP.last - CLIP.first)) * 100;
}

function Moments() {
  const snap = MOMENTS[0]?.frame ?? CLIP.first;
  const down = MOMENTS[MOMENTS.length - 1]?.frame ?? CLIP.last;
  return (
    <section
      id="film-room"
      aria-labelledby="film-room-title"
      className="border-y border-line bg-bg-2 py-20 sm:py-24"
    >
      <div className="mx-auto max-w-6xl px-4 sm:px-6">
        <SectionHeading
          id="film-room-title"
          eyebrow="The Film Room"
          title="Stop on any frame"
          intro="The playground is an interactive Film Room: scrub the play, orbit the camera, or ride along in first person. Each card opens it on a key moment."
        />

        {/* The clip as a timeline: where each moment falls between the first and last frame. */}
        <div className="mx-auto mt-14 max-w-4xl" aria-hidden="true">
          <div className="relative h-16">
            <div className="absolute inset-x-0 top-1/2 h-1 -translate-y-1/2 rounded-full bg-line-2" />
            <div
              className="absolute top-1/2 h-1 -translate-y-1/2 rounded-full bg-turf"
              style={{ left: `${clipPercent(snap)}%`, width: `${clipPercent(down) - clipPercent(snap)}%` }}
            />
            {MOMENTS.map((moment, i) => {
              const above = i % 2 === 0;
              const pos = clipPercent(moment.frame);
              const edge = pos > 92 ? "-translate-x-full" : pos < 8 ? "" : "-translate-x-1/2";
              return (
                <div key={moment.event} className="absolute inset-y-0" style={{ left: `${pos}%` }}>
                  <span className="absolute left-0 top-1/2 h-5 w-0.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-ink" />
                  <span
                    className={`absolute whitespace-nowrap font-mono text-[0.65rem] font-medium uppercase tracking-[0.12em] text-ink-2 ${edge} ${
                      above ? "top-0" : "bottom-0"
                    }`}
                  >
                    {moment.event}
                  </span>
                </div>
              );
            })}
          </div>
          <div className="mt-1 flex justify-between font-mono text-[0.65rem] uppercase tracking-[0.12em] text-ink-3">
            <span>Frame {CLIP.first}</span>
            <span>Frame {CLIP.last}</span>
          </div>
        </div>

        <ol className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {MOMENTS.map((moment) => (
            <li key={moment.event}>
              <Link
                to={`/playground?${moment.query}`}
                className="group flex h-full flex-col rounded-2xl border border-line bg-surface p-5 shadow-card transition-colors hover:border-turf"
              >
                <span className="flex items-baseline justify-between gap-3">
                  <span className="font-display text-3xl font-bold uppercase leading-none">{moment.event}</span>
                  <span className="font-mono text-xs text-ink-3">Frame {moment.frame}</span>
                </span>
                <span className="mt-3 text-ink-2">{moment.view}</span>
                <span className="mt-auto inline-flex items-center gap-1.5 pt-5 font-display text-base font-semibold uppercase tracking-[0.06em] text-turf">
                  Open in the Film Room
                  <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
                </span>
              </Link>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}

function HowItWorks() {
  return (
    <section
      id="how-it-works"
      tabIndex={-1}
      aria-labelledby="how-title"
      className="py-20 outline-none sm:py-28"
    >
      <div className="mx-auto grid max-w-6xl gap-12 px-4 sm:px-6 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:gap-16">
        <div className="lg:sticky lg:top-28 lg:self-start">
          <SectionHeading
            id="how-title"
            align="left"
            eyebrow="How it works"
            title="From two clips to a 3D replay"
            intro="Five stages, from the broadcast pixels to a lit 3D scene."
          />
          <div className="mt-8 hidden lg:block">
            <ButtonLink to="/playground" variant="secondary">
              See the result
              <ArrowRight className="h-5 w-5" />
            </ButtonLink>
          </div>
        </div>

        <ol className="relative">
          {STEPS.map((step, i) => (
            <li
              key={step.n}
              className="relative grid grid-cols-[3.25rem_minmax(0,1fr)] gap-x-4 pb-10 last:pb-0 sm:grid-cols-[4.5rem_minmax(0,1fr)] sm:gap-x-6"
            >
              {i < STEPS.length - 1 ? (
                <span
                  aria-hidden="true"
                  className="absolute bottom-0 left-[1.625rem] top-14 w-px bg-line-2 sm:left-9 sm:top-[4.75rem]"
                />
              ) : null}
              <span
                aria-hidden="true"
                className="relative flex h-13 w-13 items-center justify-center rounded-xl border border-line-2 bg-surface font-display text-2xl font-bold text-turf shadow-card sm:h-18 sm:w-18 sm:text-[2rem]"
              >
                {step.n}
              </span>
              <div className="pt-1 sm:pt-2">
                <h3 className="font-display text-2xl font-bold uppercase leading-none sm:text-3xl">{step.title}</h3>
                <p className="mt-2 font-mono text-xs font-medium uppercase tracking-[0.14em] text-ink-3">{step.kicker}</p>
                <p className="mt-3 text-ink-2">{step.body}</p>
              </div>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}

function Numbers() {
  return (
    <section aria-labelledby="numbers-title" className="turf-band text-field-ink">
      <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 sm:py-20">
        <p className="font-mono text-xs font-medium uppercase tracking-[0.18em] text-field-dim">By the numbers</p>
        <h2
          id="numbers-title"
          className="mt-3 font-display text-[2.5rem] font-bold uppercase leading-[0.95] sm:text-5xl"
        >
          Measured on the finished play
        </h2>
        <ul className="mt-10 grid grid-cols-2 gap-px overflow-hidden rounded-2xl border border-field-ink/15 bg-field-ink/15 lg:grid-cols-4">
          {STATS.map((stat) => (
            <li key={stat.label} className="bg-field p-4 sm:p-7">
              <p className="whitespace-nowrap font-mono text-[2.1rem] font-semibold leading-none tracking-[-0.03em] tabular-nums sm:text-5xl">
                {stat.value}
              </p>
              <p className="mt-3 text-[0.95rem] leading-snug text-pretty text-field-dim sm:mt-4 sm:text-base sm:leading-normal">
                {stat.label}
              </p>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

function Faq() {
  return (
    <section id="faq" tabIndex={-1} aria-labelledby="faq-title" className="py-20 outline-none sm:py-24">
      <div className="mx-auto max-w-3xl px-4 sm:px-6">
        <SectionHeading id="faq-title" eyebrow="FAQ" title="Straight answers" />
        <div className="mt-10 divide-y divide-line border-y border-line">
          {FAQS.map((item) => (
            <details key={item.q} className="group">
              <summary className="flex items-center justify-between gap-6 rounded-md py-5">
                {/* A heading inside summary is valid and lets heading navigation reach each question. */}
                <h3 className="font-display text-xl font-semibold uppercase leading-tight tracking-[0.02em] sm:text-2xl">
                  {item.q}
                </h3>
                <PlusIcon className="h-5 w-5 shrink-0 text-ink-3 transition-transform group-open:rotate-45" />
              </summary>
              <p className="pb-6 pr-8 text-ink-2">{item.a}</p>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}

function ClosingCall() {
  return (
    <section aria-labelledby="closing-title" className="turf-band text-field-ink">
      <div className="mx-auto max-w-4xl px-4 py-20 text-center sm:px-6 sm:py-24">
        <h2
          id="closing-title"
          className="font-display text-[clamp(3rem,8vw,4.5rem)] font-extrabold uppercase leading-[0.9]"
        >
          Roll the tape.
        </h2>
        <p className="mx-auto mt-4 max-w-xl text-lg text-field-dim">
          Walk around the play in the Film Room, or pull up the report on every player.
        </p>
        <div className="mt-8 flex flex-col items-stretch justify-center gap-3 sm:flex-row sm:items-center">
          <ButtonLink to="/playground" variant="chalk">
            Open the playground
            <ArrowRight className="h-5 w-5" />
          </ButtonLink>
          <ButtonLink to="/report" variant="chalk-outline">
            Generate the report
          </ButtonLink>
        </div>
      </div>
    </section>
  );
}
