# PanopticPigskin site

A static demo site for PanopticPigskin, a finished research project that turns the two
broadcast All-22 clips of one NFL play (Ravens at Chiefs, 2024 Week 1, Mahomes to Noah
Gray for 9.7 yards) into a 3D replay. Every player is placed on a calibrated field frame by
frame, posed as a full SMPL-X body fitted to both cameras, and can be viewed from any angle.

Nothing on the site is live. The clips, the Film Room's data and the report are static files
built ahead of time. There is no backend, no sign-in, no analytics and no trackers.

| Route         | What it is                                                                     |
| ------------- | ------------------------------------------------------------------------------ |
| `/`           | Landing page: hero clip, three angles, Film Room moments, how it works, numbers, FAQ |
| `/playground` | The Film Room (`public/embed/playground/index.html`) full-viewport in an iframe |
| `/report`     | "Generate report" assembles the pre-computed per-player report (`public/embed/report/index.html`) |

Stack: Vite 8, React 19, TypeScript 7, Tailwind CSS 4 (`@tailwindcss/vite`), react-router-dom 7 (`BrowserRouter`).

## Develop

Needs Node 20.19+ or 22.12+ (built and checked with Node 24 and npm 11).

```sh
npm install
npm run dev        # dev server with hot reload, http://localhost:5173
npm run build      # type-check (tsc --noEmit), then build to dist/
npm run preview    # serve dist/ locally, http://localhost:4173
```

`npm run build` fails on any TypeScript error.

## Where things live

```
index.html               app shell; resolves the theme before first paint
src/content.ts           every factual claim and number the pages show
src/pages/               Landing, Playground, Report, NotFound
src/components/          Navbar, Footer, MediaSlot (clip with placeholder), icons
src/lib/                 theme, reduced motion, iframe helpers
public/embed/playground/ the Film Room: index.html + play_joints.json
public/embed/report/     the report: index.html (self-contained)
public/media/            the four clips/images (see below)
public/favicon.svg, .ico the mark: a football seen side-on is the shape of an eye
public/_redirects        Netlify routing
vercel.json              Vercel routing
```

The stats band may only show numbers measured on the finished play. They live in `STATS` in
`src/content.ts`; do not add one there that has not been measured.

## Media files

Put these in `public/media/` (served at `/media/...`). `public/media/README.txt` has the same list.

| File            | Where it shows                                                   |
| --------------- | ---------------------------------------------------------------- |
| `follow.mp4`    | Hero clip, the replay following the play                         |
| `poster.jpg`    | Poster frame for `follow.mp4`                                    |
| `skycam.mp4`    | "Three angles": a virtual camera behind the offense              |
| `broadcast.mp4` | "Three angles": rendered from the broadcast camera's solved pose |

Until a file is there, its slot shows a styled "clip not published yet" panel; no broken
player, no console error. Use renders of the reconstruction only: nothing containing broadcast
imagery (the footer says no broadcast footage is shown). H.264 MP4, `yuv420p`,
`-movflags +faststart`, a few MB each, plays everywhere including iOS Safari.

Clips are muted and loop. They play only while on screen, have a visible pause/play control,
and never start by themselves for visitors who ask for reduced motion.

## Replacing the Film Room or the report

Drop in new files with the same names: `public/embed/playground/index.html` (plus
`play_joints.json` next to it) and `public/embed/report/index.html`. The site links to them
by those paths, so nothing else changes.

Both files are complete documents: a `<!doctype html>`, `<html lang="en">`, and a `<head>`
with `<meta charset="utf-8">` and a viewport meta around the page's own
`<title>`/`<link>`/`<style>`. A replacement needs the same shell. The doctype matters: without it the
report renders in quirks mode and the height sync below measures the wrong thing.

The Film Room takes deep links, and `/playground` passes them through to the iframe:
`/playground?cam=pocket&frame=394&r=9` (also `cam=sideline|endzone|overhead|ball|real:sideline|real:endzone`,
`cam=fpv&id=<player id>`, `theta=`). The landing page's "moments" cards use these.

How the embedding works (both pages are same-origin, so the site can read their documents):

- The report iframe is sized to its content with a `ResizeObserver` inside the frame, so the
  page scrolls as one; if the document cannot be read it keeps a tall fixed height and scrolls
  on its own.
- The report follows the site's light/dark toggle: its stylesheet reads `data-theme` on its
  root, which the site sets. The Film Room is always dark.
- Links inside the embedded report are retargeted at runtime (the file is not modified): links
  to this site open in the whole tab, anything else in a new tab.
- If a host answers a frame with this app instead of the file (the file is missing), the page
  shows a "not published here yet" panel instead of nesting the site inside itself.

## Deploy

Both hosts need the same three settings: root/base directory `site`, build command
`npm run build`, output/publish directory `dist`.

The app's pages (`/`, `/playground`, `/report`) are client-side routes. The two static pages it
embeds live under `/embed/` (`/embed/playground/index.html`, `/embed/report/index.html`), so no
static folder shares a name with an app route and the hosts serve files first, then fall back
to the app.

### Vercel

`vercel.json` is picked up automatically (framework preset: Vite). One rewrite sends every path
that is not a file to `/index.html`, except `/embed/*`, `/media/*` and `/assets/*`, which 404
when missing (a missing clip must fail as a 404, not come back as HTML).

### Netlify

`public/_redirects` is copied to `dist/_redirects` by the build: `/embed/*`, `/media/*` and
`/assets/*` serve the file when it exists and otherwise a real 404; everything else falls
through to `/index.html` (200) for client-side routing.

After a deploy on either host, check: `/playground` shows the site's Film Room page (slim bar on
top), `/embed/playground/index.html` shows the bare viewer, `/report` shows the Generate button,
and `/media/follow.mp4` plays.

## Accessibility and theming

Light and dark themes follow the OS setting until the visitor uses the toggle; the choice is
kept in `localStorage` (`pp-theme`), with every storage access wrapped so private windows and
blocked storage still work. Keyboard focus is always visible, there is a skip link, the report
sequence is announced through a live region and moves focus to the report when it arrives, and
reduced motion skips the sequence, smooth scrolling and autoplay. Layouts hold down to 390 px
wide without horizontal scrolling.
