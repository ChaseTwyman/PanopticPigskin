import { Outlet, Route, Routes } from "react-router-dom";
import { Footer } from "./components/Footer";
import { Navbar } from "./components/Navbar";
import { ScrollManager } from "./components/ScrollManager";
import { isFramedBySelf } from "./lib/frames";
import { ThemeProvider } from "./lib/theme";
import Landing from "./pages/Landing";
import NotFound from "./pages/NotFound";
import Playground from "./pages/Playground";
import Report from "./pages/Report";

function SiteLayout() {
  return (
    <div className="flex min-h-dvh flex-col">
      <Navbar />
      <main id="main" tabIndex={-1} className="flex-1 outline-none">
        <Outlet />
      </main>
      <Footer />
    </div>
  );
}

/**
 * Shown when this app finds itself inside one of its own frames: the host
 * served the app where the Film Room or report file should be. Rendering the
 * full site here would nest frames without end.
 */
function FramedNotice() {
  return (
    <div className="grid min-h-dvh place-items-center bg-screen p-6 text-center text-screen-dim">
      <p className="font-mono text-sm">This file is not published on this deployment.</p>
    </div>
  );
}

export default function App() {
  if (isFramedBySelf()) return <FramedNotice />;
  return (
    <ThemeProvider>
      <ScrollManager />
      <Routes>
        <Route element={<SiteLayout />}>
          <Route index element={<Landing />} />
          <Route path="report" element={<Report />} />
          <Route path="*" element={<NotFound />} />
        </Route>
        <Route path="playground" element={<Playground />} />
      </Routes>
    </ThemeProvider>
  );
}
