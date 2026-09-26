import type { ReactNode, SVGProps } from "react";
import type { IconName } from "../content";

type IconProps = { className?: string };

function Svg({ className, children, ...rest }: IconProps & { children: ReactNode } & SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      className={className}
      {...rest}
    >
      {children}
    </svg>
  );
}

export function ArrowRight({ className }: IconProps) {
  return (
    <Svg className={className}>
      <path d="M5 12h14M13 6l6 6-6 6" />
    </Svg>
  );
}

export function ArrowUpRight({ className }: IconProps) {
  return (
    <Svg className={className}>
      <path d="M7 17 17 7M8.5 7H17v8.5" />
    </Svg>
  );
}

export function SunIcon({ className }: IconProps) {
  return (
    <Svg className={className}>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2.5v2M12 19.5v2M4.6 4.6l1.4 1.4M18 18l1.4 1.4M2.5 12h2M19.5 12h2M4.6 19.4 6 18M18 6l1.4-1.4" />
    </Svg>
  );
}

export function MoonIcon({ className }: IconProps) {
  return (
    <Svg className={className}>
      <path d="M20 14.5A8.5 8.5 0 0 1 9.5 4a8.5 8.5 0 1 0 10.5 10.5Z" />
    </Svg>
  );
}

export function MenuIcon({ className }: IconProps) {
  return (
    <Svg className={className}>
      <path d="M4 7h16M4 12h16M4 17h16" />
    </Svg>
  );
}

export function CloseIcon({ className }: IconProps) {
  return (
    <Svg className={className}>
      <path d="M6 6l12 12M18 6 6 18" />
    </Svg>
  );
}

export function CheckIcon({ className }: IconProps) {
  return (
    <Svg className={className} strokeWidth={2.25}>
      <path d="M5 12.5l4.5 4.5L19 7.5" />
    </Svg>
  );
}

export function PlayIcon({ className }: IconProps) {
  return (
    <Svg className={className}>
      <path d="M8 5.5v13l10.5-6.5L8 5.5Z" fill="currentColor" />
    </Svg>
  );
}

export function PauseIcon({ className }: IconProps) {
  return (
    <Svg className={className}>
      <path d="M8 5.5v13M16 5.5v13" strokeWidth={3} />
    </Svg>
  );
}

export function PlusIcon({ className }: IconProps) {
  return (
    <Svg className={className}>
      <path d="M12 5v14M5 12h14" />
    </Svg>
  );
}

/** A reel of film: the empty media slot. */
export function FilmIcon({ className }: IconProps) {
  return (
    <Svg className={className}>
      <rect x="3" y="5" width="18" height="14" rx="2" />
      <path d="M7 5v14M17 5v14M3 9h4M3 15h4M17 9h4M17 15h4" />
    </Svg>
  );
}

function FieldGlyph({ className }: IconProps) {
  return (
    <Svg className={className}>
      <rect x="2.5" y="5" width="19" height="14" rx="1.5" />
      <path d="M8.5 5v14M15.5 5v14" />
      <circle cx="6" cy="9.5" r="1" fill="currentColor" />
      <circle cx="11.5" cy="14" r="1" fill="currentColor" />
      <circle cx="18.5" cy="11" r="1" fill="currentColor" />
    </Svg>
  );
}

function BodyGlyph({ className }: IconProps) {
  return (
    <Svg className={className}>
      <circle cx="12" cy="4.5" r="2" />
      <path d="M12 7v7M12 9.5l-4.5 3M12 9.5l4.5 2.5M12 14l-3 6.5M12 14l3.5 6" />
    </Svg>
  );
}

function OrbitGlyph({ className }: IconProps) {
  return (
    <Svg className={className}>
      <ellipse cx="12" cy="12" rx="9.5" ry="4.5" />
      <circle cx="12" cy="12" r="2" fill="currentColor" />
      <path d="M18.5 5.5l2.3 1.4-1.2 2.4" />
    </Svg>
  );
}

function CameraGlyph({ className }: IconProps) {
  return (
    <Svg className={className}>
      <rect x="2.5" y="7" width="13" height="10" rx="1.5" />
      <path d="M15.5 10.5l6-3v9l-6-3" />
      <path d="M6 17v3.5M12 17v3.5" />
    </Svg>
  );
}

function ReportGlyph({ className }: IconProps) {
  return (
    <Svg className={className}>
      <rect x="4" y="3" width="16" height="18" rx="2" />
      <path d="M8 16v-3M12 16V9M16 16v-5" />
    </Svg>
  );
}

function RulerGlyph({ className }: IconProps) {
  return (
    <Svg className={className}>
      <path d="M3.5 16.5 16.5 3.5l4 4-13 13-4-4Z" />
      <path d="M7 13l2 2M10 10l2 2M13 7l2 2" />
    </Svg>
  );
}

const GLYPHS: Record<IconName, (props: IconProps) => ReactNode> = {
  field: FieldGlyph,
  body: BodyGlyph,
  orbit: OrbitGlyph,
  camera: CameraGlyph,
  report: ReportGlyph,
  ruler: RulerGlyph,
};

export function FeatureIcon({ name, className }: { name: IconName; className?: string }) {
  const Glyph = GLYPHS[name];
  return <Glyph className={className} />;
}
