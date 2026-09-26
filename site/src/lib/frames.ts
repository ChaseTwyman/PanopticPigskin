// Helpers for the two embedded static pages (/embed/playground/index.html and
// /embed/report/index.html). Both are served from this site's own origin, so the
// parent page can read their documents; every access is still guarded.

/** The document inside a same-origin iframe, or null if it cannot be read. */
export function frameDocument(frame: HTMLIFrameElement | null): Document | null {
  if (!frame) return null;
  try {
    return frame.contentDocument ?? frame.contentWindow?.document ?? null;
  } catch {
    return null;
  }
}

/**
 * True when a frame loaded this app's own shell instead of the static page:
 * the file is missing from the deployment, or the host rewrote the request.
 */
export function isAppShell(doc: Document): boolean {
  return doc.querySelector('meta[name="pp-shell"]') !== null;
}

/** True when this app is itself running inside a frame of a same-site page. */
export function isFramedBySelf(): boolean {
  try {
    return window.self !== window.top && window.top?.location.origin === window.location.origin;
  } catch {
    return false;
  }
}

/**
 * Links inside an embedded page should not navigate the frame: pages of this
 * site take over the whole tab, anything else opens in a new tab. In-page
 * anchors are left alone. The file on disk is not changed.
 */
export function retargetLinks(doc: Document): void {
  const here = doc.location?.pathname ?? "";
  doc.querySelectorAll<HTMLAnchorElement>("a[href]").forEach((link) => {
    const raw = link.getAttribute("href") ?? "";
    if (raw.startsWith("#")) return;
    let url: URL;
    try {
      url = new URL(raw, doc.baseURI);
    } catch {
      return;
    }
    if (url.origin === window.location.origin) {
      if (url.pathname === here && url.hash) return;
      link.target = "_top";
    } else {
      link.target = "_blank";
      link.rel = "noopener noreferrer";
    }
  });
}
