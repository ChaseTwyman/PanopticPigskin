import type { ReactNode } from "react";

type Props = {
  id?: string;
  eyebrow: string;
  title: ReactNode;
  intro?: ReactNode;
  align?: "center" | "left";
};

export function SectionHeading({ id, eyebrow, title, intro, align = "center" }: Props) {
  const centered = align === "center";
  return (
    <div className={centered ? "mx-auto max-w-3xl text-center" : "max-w-2xl"}>
      <p className="font-mono text-xs font-medium uppercase tracking-[0.18em] text-turf">{eyebrow}</p>
      <h2
        id={id}
        className="mt-3 font-display text-[2.5rem] font-bold uppercase leading-[0.95] tracking-[0.005em] sm:text-5xl"
      >
        {title}
      </h2>
      {intro ? <p className="mt-4 text-lg text-ink-2">{intro}</p> : null}
    </div>
  );
}
