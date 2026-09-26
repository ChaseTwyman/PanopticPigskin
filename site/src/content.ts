// All site copy that states a fact about the project lives here, so it can be
// checked in one place. Numbers come from the finished reconstruction; do not
// add a figure here that has not been measured.

export type IconName = "field" | "body" | "orbit" | "camera" | "report" | "ruler";

export type Feature = {
  icon: IconName;
  title: string;
  body: string;
  link?: { to: string; label: string };
};

export const FEATURES: Feature[] = [
  {
    icon: "field",
    title: "Every player, every frame",
    body: "All 22 players placed on a calibrated field, frame by frame, from the two broadcast cameras.",
  },
  {
    icon: "body",
    title: "Bodies, not boxes",
    body: "Each player is a full SMPL-X human body fitted to both cameras at once, not a dot or a bounding box.",
  },
  {
    icon: "orbit",
    title: "Any seat in the stadium",
    body: "Orbit the play, or jump to presets for the sideline, the endzone, or first person through a player's eyes.",
    link: { to: "/playground", label: "Open the playground" },
  },
  {
    icon: "camera",
    title: "The broadcast's own framing",
    body: "Both broadcast cameras are solved on every frame, so the replay can be rendered from exactly where each one stood and pointed.",
  },
  {
    icon: "report",
    title: "A report on every player",
    body: "Separation at the throw, pressure in the pocket and a grade for each of the 22, all built from the tracking.",
    link: { to: "/report", label: "Generate the report" },
  },
  {
    icon: "ruler",
    title: "Measured, then modelled",
    body: "Placement and poses are fitted to the film. What is modelled instead (the gait, the throw, catch and tackle, where heads point) is said plainly.",
  },
];

export type Angle = {
  n: number;
  name: string;
  src: string;
  title: string;
  body: string;
};

export const ANGLES: Angle[] = [
  {
    n: 2,
    name: "Skycam",
    src: "/media/skycam.mp4",
    title: "Behind the offense",
    body: "A virtual camera behind the offense, looking downfield as the play develops.",
  },
  {
    n: 3,
    name: "Broadcast",
    src: "/media/broadcast.mp4",
    title: "From the broadcast camera's own pose",
    body: "Rendered from the pose solved for the broadcast camera on every frame: the broadcast's framing, with every body drawn by the reconstruction.",
  },
];

export type Step = { n: string; title: string; kicker: string; body: string };

export const STEPS: Step[] = [
  {
    n: "01",
    title: "Cameras",
    kicker: "Solved on every frame",
    body: "Both broadcast cameras are solved on every frame from the field's own paint: yard lines, hash marks and numbers. The players' known height fixes the lens.",
  },
  {
    n: "02",
    title: "Players",
    kicker: "Tracked, joined, named",
    body: "Players are detected and tracked in each camera, joined across the two views and named by the numbers on their jerseys. Where the tracker slips in a pile, the film decides.",
  },
  {
    n: "03",
    title: "Placement",
    kicker: "Feet on the turf",
    body: "Feet are traced to the turf from both cameras. Where neither camera can place a man, his helmet is read off both films and triangulated.",
  },
  {
    n: "04",
    title: "Pose",
    kicker: "One body, two views",
    body: "A keypoint model fine-tuned on this play's own frames finds the joints, and a full SMPL-X body is fitted to both cameras at once.",
  },
  {
    n: "05",
    title: "Render",
    kicker: "Splats, kits, stadium light",
    body: "Bodies are drawn as Gaussian splats in the kits the film shows, lit by a stadium key light, inside a bowl of seats.",
  },
];

// The only numbers the stats band may show. Each was measured on the finished play.
// NBSP ( ) keeps a number and its unit on one line.
export const STATS = [
  { value: "100%", label: "of frames from snap to whistle with exactly 11 players a side" },
  { value: "0", label: "live frames where a body jumps over 0.25 m" },
  { value: "2", label: "broadcast cameras, each solved on every frame" },
  { value: "6.7 s", label: "of play, 400 frames at 59.94 fps" },
] as const;

export const FAQS = [
  {
    q: "Is it live?",
    a: "No. It is a finished reconstruction of one play, pre-rendered. The clips, the Film Room's data and the report are all static files built ahead of time.",
  },
  {
    q: "What is measured, and what is modelled?",
    a: "Placement and poses are fitted to the film. The running gait, the throw, catch and tackle poses, and where a player's head points are modelled.",
  },
  {
    q: "Why a plain field?",
    a: "The public renders use a painted field rather than the broadcast's own turf imagery.",
  },
  {
    q: "What are the limits?",
    a: "Piles are the weakest part: bodies there are seen clearly by neither camera for long stretches.",
  },
] as const;

// Key moments of the play, read off the film. Frames are the Film Room's own
// frame numbers (59.94 fps clip frames, sampled every second frame), so the
// counter in the viewer shows the same number as the card.
export const CLIP = { first: 216, last: 614 } as const;

export type Moment = { event: string; frame: number; view: string; query: string };

export const MOMENTS: Moment[] = [
  { event: "Snap", frame: 394, view: "From the pocket", query: "cam=pocket&frame=394&r=9" },
  { event: "Release", frame: 530, view: "Riding with the ball", query: "cam=ball&frame=530" },
  { event: "Catch", frame: 562, view: "From behind the defense", query: "cam=endzone&frame=562" },
  { event: "Down", frame: 608, view: "Through the broadcast sideline camera", query: "cam=real:sideline&frame=608" },
];

export const REPORT_STAGES = [
  "Reading 22 player tracks",
  "Measuring separation at the throw",
  "Scoring the pocket",
  "Grading 22 players",
] as const;
