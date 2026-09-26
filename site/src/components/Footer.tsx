import { Link } from "react-router-dom";
import { GITHUB_URL } from "./Navbar";
import { Wordmark } from "./Wordmark";

const COL_TITLE = "font-mono text-xs font-medium uppercase tracking-[0.18em] text-ink-3";
const COL_LINK = "text-ink-2 underline-offset-4 hover:text-ink hover:underline";

export function Footer() {
  return (
    <footer className="border-t border-line bg-bg-2">
      <div className="mx-auto max-w-6xl px-4 py-14 sm:px-6">
        <div className="grid grid-cols-2 gap-x-6 gap-y-10 md:grid-cols-[1.6fr_1fr_1fr]">
          <div className="col-span-2 md:col-span-1">
            <Wordmark />
            <p className="mt-4 max-w-sm text-ink-2">
              A 3D reconstruction of one NFL play, rebuilt from its two broadcast{" "}
              <span className="whitespace-nowrap">All-22</span> clips. Everything here is built ahead of time; nothing
              runs live.
            </p>
          </div>

          <nav aria-labelledby="footer-explore">
            <h2 id="footer-explore" className={COL_TITLE}>
              Explore
            </h2>
            <ul className="mt-4 space-y-2.5">
              <li>
                <Link to="/playground" className={COL_LINK}>
                  Playground
                </Link>
              </li>
              <li>
                <Link to="/report" className={COL_LINK}>
                  Report
                </Link>
              </li>
              <li>
                <Link to="/#how-it-works" className={COL_LINK}>
                  How it works
                </Link>
              </li>
              <li>
                <Link to="/#faq" className={COL_LINK}>
                  FAQ
                </Link>
              </li>
            </ul>
          </nav>

          <div>
            <h2 className={COL_TITLE}>Project</h2>
            <ul className="mt-4 space-y-2.5">
              <li>
                <a href={GITHUB_URL} className={COL_LINK}>
                  GitHub
                </a>
              </li>
              <li className="text-ink-2">Built on one RTX 4080</li>
            </ul>
          </div>
        </div>

        <div className="chalk-rule mt-12" aria-hidden="true" />

        <div className="mt-6 flex flex-col gap-2 text-sm text-ink-3 sm:flex-row sm:items-start sm:justify-between sm:gap-8">
          <p>No broadcast footage is shown on this site.</p>
          <p className="sm:text-right">Not affiliated with the NFL or its clubs.</p>
        </div>
      </div>
    </footer>
  );
}
