import { ButtonLink } from "../components/ButtonLink";
import { useDocumentTitle } from "../lib/useDocumentTitle";

export default function NotFound() {
  useDocumentTitle("Incomplete pass · PanopticPigskin");
  return (
    <section className="relative isolate overflow-hidden">
      <div aria-hidden="true" className="field-lines hero-field pointer-events-none absolute inset-0 -z-10" />
      <div className="mx-auto max-w-3xl px-4 py-24 text-center sm:px-6 sm:py-32">
        <p className="font-mono text-xs font-medium uppercase tracking-[0.18em] text-turf">404 · Flag on the play</p>
        <h1 className="mt-4 font-display text-[clamp(3rem,10vw,5.5rem)] font-extrabold uppercase leading-[0.9]">
          Incomplete pass
        </h1>
        <p className="mx-auto mt-5 max-w-md text-lg text-ink-2">There is no page at this address.</p>
        <div className="mt-8 flex justify-center">
          <ButtonLink to="/">Back to the start</ButtonLink>
        </div>
      </div>
    </section>
  );
}
