import { useTheme } from "../lib/theme";
import { MoonIcon, SunIcon } from "./Icons";

export function ThemeToggle({ className = "" }: { className?: string }) {
  const { theme, toggle } = useTheme();
  const dark = theme === "dark";
  return (
    <button
      type="button"
      onClick={toggle}
      aria-pressed={dark}
      aria-label="Dark theme"
      title={dark ? "Night game: switch to the light theme" : "Day game: switch to the dark theme"}
      className={`inline-flex h-10 w-10 items-center justify-center rounded-lg border border-line bg-surface text-ink-2 transition-colors hover:border-line-2 hover:text-ink ${className}`}
    >
      {dark ? <SunIcon className="h-5 w-5" /> : <MoonIcon className="h-5 w-5" />}
    </button>
  );
}
