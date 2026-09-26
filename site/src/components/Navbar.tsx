import { useEffect, useRef, useState } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import { buttonClass } from "./ButtonLink";
import { CloseIcon, MenuIcon } from "./Icons";
import { ThemeToggle } from "./ThemeToggle";
import { Wordmark } from "./Wordmark";

/** The project's source repository. */
export const GITHUB_URL = "https://github.com/ChaseTwyman/PanopticPigskin";

type Item = { to: string; label: string; route: boolean };

const ITEMS: Item[] = [
  { to: "/playground", label: "Playground", route: true },
  { to: "/report", label: "Report", route: true },
  { to: "/#how-it-works", label: "How it works", route: false },
];

const LINK =
  "relative rounded-md px-3 py-2 font-display text-[1.05rem] font-semibold uppercase leading-none tracking-[0.06em] transition-colors";
const IDLE = "text-ink-2 hover:bg-surface-2 hover:text-ink";
const ACTIVE =
  "text-ink after:absolute after:inset-x-3 after:-bottom-px after:h-0.5 after:rounded-full after:bg-turf";

function DesktopLink({ item }: { item: Item }) {
  if (!item.route) {
    return (
      <Link to={item.to} className={`${LINK} ${IDLE}`}>
        {item.label}
      </Link>
    );
  }
  return (
    <NavLink to={item.to} className={({ isActive }) => `${LINK} ${isActive ? ACTIVE : IDLE}`}>
      {item.label}
    </NavLink>
  );
}

export function Navbar({ compact = false }: { compact?: boolean }) {
  const [open, setOpen] = useState(false);
  const { key } = useLocation();
  const menuButton = useRef<HTMLButtonElement>(null);

  // Any navigation closes the menu, including a link to the page already shown.
  useEffect(() => {
    setOpen(false);
  }, [key]);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
        menuButton.current?.focus();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <header className="sticky top-0 z-50 border-b border-line bg-bg/85 backdrop-blur-md">
      <a
        href="#main"
        className="sr-only rounded-md bg-ink font-medium text-bg focus:not-sr-only focus:absolute focus:left-3 focus:top-3 focus:z-50 focus:px-4 focus:py-2"
      >
        Skip to content
      </a>
      <nav
        aria-label="Main"
        className={`mx-auto flex items-center gap-3 px-4 sm:px-6 ${compact ? "h-12" : "h-16 max-w-6xl"}`}
      >
        <Wordmark compact={compact} />

        <ul className="ml-auto hidden items-center gap-1 md:flex">
          {ITEMS.map((item) => (
            <li key={item.to}>
              <DesktopLink item={item} />
            </li>
          ))}
          <li>
            <a href={GITHUB_URL} className={`${LINK} ${IDLE}`}>
              GitHub
            </a>
          </li>
        </ul>

        <div className="ml-auto flex items-center gap-2 md:ml-1">
          <ThemeToggle className={compact ? "h-9 w-9" : ""} />
          {compact ? null : (
            // The wrapper owns visibility: the button's own inline-flex would override `hidden`.
            <div className="hidden lg:block">
              <Link to="/playground" className={buttonClass("primary", "!min-h-10 !px-4 !text-base")}>
                Open the playground
              </Link>
            </div>
          )}
          <button
            ref={menuButton}
            type="button"
            className={`inline-flex items-center justify-center rounded-lg border border-line bg-surface text-ink md:hidden ${
              compact ? "h-9 w-9" : "h-10 w-10"
            }`}
            aria-expanded={open}
            aria-controls="mobile-menu"
            onClick={() => setOpen((value) => !value)}
          >
            {open ? <CloseIcon className="h-5 w-5" /> : <MenuIcon className="h-5 w-5" />}
            <span className="sr-only">Menu</span>
          </button>
        </div>
      </nav>

      {open ? (
        <div id="mobile-menu" className="border-t border-line bg-bg md:hidden">
          <ul className="mx-auto flex max-w-6xl flex-col px-4 py-3 sm:px-6">
            {ITEMS.map((item) => (
              <li key={item.to}>
                {item.route ? (
                  <NavLink
                    to={item.to}
                    className={({ isActive }) =>
                      `block rounded-md px-3 py-3 font-display text-xl font-semibold uppercase tracking-[0.05em] ${
                        isActive ? "bg-surface-2 text-ink" : "text-ink-2 hover:bg-surface-2 hover:text-ink"
                      }`
                    }
                  >
                    {item.label}
                  </NavLink>
                ) : (
                  <Link
                    to={item.to}
                    className="block rounded-md px-3 py-3 font-display text-xl font-semibold uppercase tracking-[0.05em] text-ink-2 hover:bg-surface-2 hover:text-ink"
                  >
                    {item.label}
                  </Link>
                )}
              </li>
            ))}
            <li>
              <a
                href={GITHUB_URL}
                className="block rounded-md px-3 py-3 font-display text-xl font-semibold uppercase tracking-[0.05em] text-ink-2 hover:bg-surface-2 hover:text-ink"
              >
                GitHub
              </a>
            </li>
          </ul>
        </div>
      ) : null}
    </header>
  );
}
