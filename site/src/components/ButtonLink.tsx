import type { ReactNode } from "react";
import { Link } from "react-router-dom";

export type ButtonVariant = "primary" | "secondary" | "chalk" | "chalk-outline";

const VARIANTS: Record<ButtonVariant, string> = {
  primary: "bg-turf text-on-turf shadow-card hover:bg-turf-strong",
  secondary: "border border-line-2 bg-surface text-ink hover:border-ink-3 hover:bg-surface-2",
  chalk: "bg-field-ink text-field hover:bg-white",
  "chalk-outline": "border border-field-ink/50 text-field-ink hover:border-field-ink hover:bg-field-ink/10",
};

export const BUTTON_BASE =
  "inline-flex min-h-12 items-center justify-center gap-2 rounded-lg px-5 py-2.5 font-display text-lg font-semibold uppercase leading-none tracking-[0.06em] transition-colors";

export function buttonClass(variant: ButtonVariant = "primary", extra = ""): string {
  return `${BUTTON_BASE} ${VARIANTS[variant]} ${extra}`.trim();
}

type Props = {
  children: ReactNode;
  variant?: ButtonVariant;
  className?: string;
} & ({ to: string; href?: never } | { href: string; to?: never });

/** A link styled as a button: `to` for app routes, `href` for static files. */
export function ButtonLink({ children, variant = "primary", className = "", ...target }: Props) {
  const cls = buttonClass(variant, className);
  if (target.to !== undefined) {
    return (
      <Link to={target.to} className={cls}>
        {children}
      </Link>
    );
  }
  return (
    <a href={target.href} className={cls}>
      {children}
    </a>
  );
}
