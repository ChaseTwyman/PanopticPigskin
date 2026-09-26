import { useEffect } from "react";
import { useLocation, useNavigationType } from "react-router-dom";
import { prefersReducedMotion } from "../lib/motion";

/**
 * BrowserRouter does not manage scroll or focus. New pages start at the top
 * with focus on <main> (the clicked link is gone, and focus would otherwise
 * drop to <body> with no cue that a new page loaded); links with a hash land
 * on their section; back/forward is left to the browser.
 */
export function ScrollManager() {
  const { pathname, hash, key } = useLocation();
  const navigation = useNavigationType();

  useEffect(() => {
    if (hash.length > 1) {
      let id = hash.slice(1);
      try {
        id = decodeURIComponent(id);
      } catch {
        /* keep the raw id */
      }
      const frame = requestAnimationFrame(() => {
        const target = document.getElementById(id);
        if (!target) return;
        target.scrollIntoView({ behavior: prefersReducedMotion() ? "instant" : "smooth", block: "start" });
        if (target.hasAttribute("tabindex")) target.focus({ preventScroll: true });
      });
      return () => cancelAnimationFrame(frame);
    }
    if (navigation !== "POP") {
      window.scrollTo({ top: 0, left: 0, behavior: "instant" });
      document.getElementById("main")?.focus({ preventScroll: true });
    }
    return undefined;
    // `key` changes on every navigation, so the same link clicked twice still scrolls.
  }, [pathname, hash, key, navigation]);

  return null;
}
