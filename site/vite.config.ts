import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// Plain static SPA. Everything under public/ (the Film Room, the report, the
// media slots) is copied to dist/ untouched and served next to the app.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  base: "/",
  build: {
    target: "es2022",
    // play_001_joints.json lives in public/ and is copied, not bundled,
    // so the only large chunk here is React itself.
    chunkSizeWarningLimit: 600,
  },
});
