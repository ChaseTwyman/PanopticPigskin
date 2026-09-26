PanopticPigskin site media
==========================

The landing page uses these four files in this folder (public/media/),
served at /media/<name>. All four are renders of the reconstruction on a
painted field. If a file is missing, its slot on the page shows a styled
"not published yet" panel.

  follow.mp4     Hero clip: the rendered replay following the play.
                 Muted, looping, autoplays (paused for visitors who ask for
                 reduced motion). 16:9.

  poster.jpg     Poster frame for follow.mp4, shown while the clip loads.
                 16:9, same size as the clip.

  skycam.mp4     "Three angles" section: a virtual camera behind the offense.
                 Muted, looping. 16:9.

  broadcast.mp4  "Three angles" section: the replay rendered from the
                 broadcast camera's own solved pose. Muted, looping. 16:9.

Rules for what goes here
------------------------
- Renders of the reconstruction only. Nothing that contains broadcast
  imagery: no footage, no frames, no broadcast turf texture. The footer of
  the site says "No broadcast footage is shown on this site."
- H.264 MP4 (yuv420p, +faststart) plays everywhere, including iOS Safari.
  Keep each clip small (a few MB): they autoplay on page load.
- Keep the file names exactly as above; the pages reference them by name.
