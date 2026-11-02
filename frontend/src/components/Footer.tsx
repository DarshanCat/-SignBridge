/** Attribution, licence and honesty notices shown on every page of every deployment. */
export function Footer() {
  return (
    <footer className="mx-auto mt-10 max-w-6xl border-t border-white/10 px-4 py-6 text-xs leading-relaxed text-slate-400" aria-label="About and licences">
      <p>
        <strong className="text-slate-300">Research prototype.</strong> SignBridge is an academic project, not a certified translation or interpreting service. Do not rely on it
        for medical, legal or safety communication.
      </p>
      <p className="mt-2">
        <strong className="text-slate-300">Sign clips are not signer-reviewed.</strong> The avatar signs are automatic retargets from dataset samples and have not been checked
        by a Deaf or hearing ISL signer; they can be wrong or unnatural.
      </p>
      <p className="mt-2">
        <strong className="text-slate-300">Data and licence.</strong> The recognizer and the avatar clips are derived from the INCLUDE dataset: Sridhar et al., &ldquo;INCLUDE: A Large
        Scale Dataset for Indian Sign Language Recognition&rdquo;, ACM Multimedia 2020 (
        <a className="underline" href="https://zenodo.org/records/4010759" target="_blank" rel="noreferrer noopener">
          zenodo.org/records/4010759
        </a>
        ). INCLUDE-derived material is shared for <strong className="text-slate-300">non-commercial use only</strong> under{" "}
        <a className="underline" href="https://creativecommons.org/licenses/by-nc-sa/4.0/" target="_blank" rel="noreferrer noopener">
          CC BY-NC-SA 4.0
        </a>{" "}
        with attribution. Results are on the authors&apos; predefined split; signer independence is not verified.
      </p>
      <p className="mt-2">Your camera video stays in your browser; only hand and body landmarks are sent to the server, and nothing is stored.</p>
    </footer>
  );
}
