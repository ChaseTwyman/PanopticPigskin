import { Link } from "react-router-dom";

/** The mark: a football seen side-on is the shape of an eye. */
export function LogoMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden="true" focusable="false">
      <path d="M1.5 16C7 6.5 25 6.5 30.5 16 25 25.5 7 25.5 1.5 16Z" fill="var(--pp-turf)" />
      <path d="M8.3 12.1v7.8M23.7 12.1v7.8" stroke="#f5f4ec" strokeWidth="1.7" strokeLinecap="round" />
      <circle cx="16" cy="16" r="4.9" fill="#f5f4ec" />
      <circle cx="16" cy="16" r="2.3" fill="#101812" />
    </svg>
  );
}

export function Wordmark({ compact = false }: { compact?: boolean }) {
  return (
    <Link
      to="/"
      aria-label="PanopticPigskin home"
      className="inline-flex shrink-0 items-center gap-2 rounded-md text-ink"
    >
      <LogoMark className={compact ? "h-6 w-6" : "h-7 w-7 sm:h-8 sm:w-8"} />
      <span
        className={`font-display font-bold uppercase leading-none tracking-[0.03em] ${
          compact ? "text-lg" : "text-xl sm:text-[1.45rem]"
        }`}
      >
        Panoptic<span className="text-turf">Pigskin</span>
      </span>
    </Link>
  );
}
