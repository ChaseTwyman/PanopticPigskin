import { useEffect, useRef, useState } from "react";
import { useReducedMotion } from "../lib/motion";
import { FilmIcon, PauseIcon, PlayIcon } from "./Icons";

type Status = "loading" | "ready" | "missing";
type Intent = "auto" | "play" | "pause";

type Props = {
  /** Path under public/, e.g. /media/follow.mp4 */
  src: string;
  poster?: string;
  /** Short name shown on the empty slot, e.g. "Follow cam". */
  label: string;
  /** What the clip shows, for screen readers. */
  description: string;
  /** The hero clip starts loading at once; the others fetch metadata only. */
  eager?: boolean;
};

/**
 * A muted, looping clip that degrades to a styled panel when the file is not
 * there. The <video> stays invisible until the browser has read real video
 * metadata, and is removed on error, so a missing file never shows a broken
 * player. Plays only while on screen; never starts by itself for visitors who
 * ask for reduced motion, and always has a visible pause/play control.
 */
export function MediaSlot({ src, poster, label, description, eager = false }: Props) {
  const reduced = useReducedMotion();
  const box = useRef<HTMLDivElement>(null);
  const video = useRef<HTMLVideoElement>(null);
  const [status, setStatus] = useState<Status>("loading");
  const [intent, setIntent] = useState<Intent>("auto");
  const [inView, setInView] = useState(false);
  const [playing, setPlaying] = useState(false);

  // A clip that failed, or finished reading metadata, before the listeners ran.
  useEffect(() => {
    const el = video.current;
    if (!el) return;
    if (el.error) setStatus("missing");
    else if (el.readyState >= HTMLMediaElement.HAVE_METADATA) setStatus("ready");
  }, []);

  useEffect(() => {
    const el = box.current;
    if (!el) return;
    if (typeof IntersectionObserver === "undefined") {
      setInView(true);
      return;
    }
    // A low threshold: on a laptop screen only the top fifth of the hero clip
    // shows above the fold, and it should already be playing.
    const observer = new IntersectionObserver(([entry]) => setInView(entry?.isIntersecting ?? false), {
      threshold: 0.05,
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const wantsPlay = intent === "play" || (intent === "auto" && !reduced);

  // The only thing that starts or stops a clip. There is deliberately no
  // `autoplay` attribute: it would start clips that are off screen and make the
  // browser download them in full; this effect autoplays each clip (muted,
  // inline) once it is on screen, which is what the attribute was for.
  useEffect(() => {
    const el = video.current;
    if (!el || status !== "ready") return;
    if (wantsPlay && inView) {
      el.muted = true;
      el.play().catch(() => {
        /* autoplay refused (power saving, data saver): the play button stays available */
      });
    } else {
      el.pause();
    }
  }, [status, wantsPlay, inView]);

  const ready = status === "ready";

  return (
    <div ref={box} className="relative aspect-video w-full overflow-hidden rounded-xl bg-screen">
      {ready ? null : <EmptySlot label={label} src={src} missing={status === "missing"} />}

      {status === "missing" ? null : (
        <video
          ref={video}
          className={`absolute inset-0 h-full w-full object-cover transition-opacity duration-700 ${
            ready ? "opacity-100" : "opacity-0"
          }`}
          src={src}
          poster={poster}
          muted
          loop
          playsInline
          preload={eager ? "auto" : "metadata"}
          aria-label={description}
          onLoadedMetadata={() => setStatus("ready")}
          onError={() => setStatus("missing")}
          onPlay={() => setPlaying(true)}
          onPause={() => setPlaying(false)}
        />
      )}

      {ready ? (
        <button
          type="button"
          onClick={() => setIntent(playing ? "pause" : "play")}
          aria-label={playing ? `Pause the ${label} clip` : `Play the ${label} clip`}
          className="absolute bottom-3 right-3 inline-flex h-10 items-center gap-2 rounded-full bg-black/65 px-3.5 text-white backdrop-blur-sm transition-colors hover:bg-black/80"
        >
          {playing ? <PauseIcon className="h-4 w-4" /> : <PlayIcon className="h-4 w-4" />}
          <span aria-hidden="true" className="font-mono text-[0.7rem] font-medium uppercase tracking-[0.14em]">
            {playing ? "Pause" : "Play"}
          </span>
        </button>
      ) : null}
    </div>
  );
}

function EmptySlot({ label, src, missing }: { label: string; src: string; missing: boolean }) {
  if (!missing) return <div className="screen-lines absolute inset-0" aria-hidden="true" />;
  return (
    <div
      className="screen-lines absolute inset-0 grid place-items-center p-4 text-center"
      role="img"
      aria-label={`${label}: clip not published yet`}
    >
      <div>
        <FilmIcon className="mx-auto h-7 w-7 text-screen-dim sm:h-8 sm:w-8" />
        <p className="mt-2 font-display text-xl font-bold uppercase leading-none tracking-[0.05em] text-screen-ink sm:mt-3 sm:text-2xl">
          {label}
        </p>
        <p className="mt-1.5 text-sm text-screen-dim">Clip not published yet</p>
        <p className="mt-1 font-mono text-[0.68rem] text-screen-dim">{src}</p>
      </div>
    </div>
  );
}
