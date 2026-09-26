import { useSyncExternalStore } from "react";

const QUERY = "(prefers-reduced-motion: reduce)";

function read(): boolean {
  try {
    return window.matchMedia(QUERY).matches;
  } catch {
    return false;
  }
}

function subscribe(onChange: () => void): () => void {
  let query: MediaQueryList;
  try {
    query = window.matchMedia(QUERY);
  } catch {
    return () => {};
  }
  query.addEventListener("change", onChange);
  return () => query.removeEventListener("change", onChange);
}

/** True while the visitor asks for reduced motion; updates if they change the setting. */
export function useReducedMotion(): boolean {
  return useSyncExternalStore(subscribe, read, () => false);
}

/** One-off read, for event handlers and effects that should not re-run on a change. */
export const prefersReducedMotion = read;
