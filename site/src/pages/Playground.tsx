import { useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { ArrowUpRight } from "../components/Icons";
import { Navbar } from "../components/Navbar";
import { frameDocument, isAppShell } from "../lib/frames";
import { useDocumentTitle } from "../lib/useDocumentTitle";

const VIEWER = "/embed/playground/index.html";

// Deep-link parameters the Film Room understands (?cam=pocket&frame=394&r=9).
const PASS_THROUGH = ["cam", "frame", "id", "r", "theta"] as const;

function viewerUrl(search: string): string {
  const incoming = new URLSearchParams(search);
  const outgoing = new URLSearchParams();
  for (const key of PASS_THROUGH) {
    const value = incoming.get(key);
    if (value) outgoing.set(key, value);
  }
  const query = outgoing.toString();
  return query ? `${VIEWER}?${query}` : VIEWER;
}

// The Film Room paints this colour; the frame shows it while loading.
const VIEWER_GROUND = "#14161a";

export default function Playground() {
  useDocumentTitle("Film Room · PanopticPigskin");
  const { search } = useLocation();
  const src = viewerUrl(search);

  return (
    <div className="flex h-dvh flex-col bg-bg">
      <Navbar compact />
      <main id="main" tabIndex={-1} className="flex min-h-0 flex-1 flex-col outline-none">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 border-b border-line bg-bg-2 px-4 py-2 sm:px-6">
          <h1 className="font-display text-lg font-bold uppercase leading-none tracking-[0.05em]">Film Room</h1>
          <p className="order-3 w-full text-sm leading-snug text-ink-2 sm:order-none sm:w-auto sm:flex-1">
            Drag to orbit. Presets jump to the sideline, the endzone or first person.
          </p>
          <a
            href={src}
            className="ml-auto inline-flex items-center gap-1 rounded-md py-1 font-display text-base font-semibold uppercase leading-none tracking-[0.06em] text-turf hover:underline hover:underline-offset-4 sm:ml-0"
          >
            Open full screen
            <ArrowUpRight className="h-4 w-4" />
          </a>
        </div>

        <div className="relative min-h-0 flex-1" style={{ backgroundColor: VIEWER_GROUND }}>
          <ViewerFrame key={src} src={src} />
        </div>
      </main>
    </div>
  );
}

function ViewerFrame({ src }: { src: string }) {
  const frame = useRef<HTMLIFrameElement>(null);
  const [loaded, setLoaded] = useState(false);
  const [missing, setMissing] = useState(false);

  const onLoad = () => {
    const doc = frameDocument(frame.current);
    // The host answered with this app instead of the viewer: the file is not deployed.
    if (doc && isAppShell(doc)) setMissing(true);
    setLoaded(true);
  };

  if (missing) {
    return (
      <div className="absolute inset-0 grid place-items-center p-6 text-center">
        <div>
          <p className="font-display text-2xl font-bold uppercase tracking-[0.04em] text-screen-ink">
            The Film Room is not published here yet
          </p>
          <p className="mt-2 font-mono text-xs text-screen-dim">{VIEWER}</p>
        </div>
      </div>
    );
  }

  return (
    <>
      {loaded ? null : (
        <div
          aria-hidden="true"
          className="absolute inset-0 grid place-items-center font-display text-2xl uppercase tracking-[0.06em] text-screen-dim"
        >
          Loading the Film Room
        </div>
      )}
      <iframe
        ref={frame}
        src={src}
        title="Film Room: interactive 3D replay of the play"
        allow="fullscreen"
        onLoad={onLoad}
        className="absolute inset-0 h-full w-full border-0"
      />
    </>
  );
}
