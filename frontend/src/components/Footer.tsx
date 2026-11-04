/** Attribution, licence and honesty notices shown on every page of every deployment. */
export function Footer() {
  return (
    <footer className="mx-auto mt-6 max-w-[1360px] border-t border-line px-4 py-6 text-sm font-medium leading-relaxed text-ink2 sm:px-8" aria-label="About and licences">
      <p>
        <strong className="text-ink">Research prototype.</strong> SignBridge is an academic project, not a certified translation or interpreting service. Do not rely on it
        for medical, legal or safety communication.
      </p>
      <p className="mt-2">
        <strong className="text-ink">Sign clips are not signer-reviewed.</strong> The avatar signs are automatic retargets from dataset samples and have not been checked
        by a Deaf or hearing ISL signer; they can be wrong or unnatural. The avatar&apos;s face (blinking, brows) and head movements are rule-based approximations.
      </p>
      <p className="mt-2">
        <strong className="text-ink">Data and licence.</strong> The recognizer and the avatar clips are derived from the INCLUDE dataset: Sridhar et al., &ldquo;INCLUDE: A Large
        Scale Dataset for Indian Sign Language Recognition&rdquo;, ACM Multimedia 2020 (
        <a className="font-bold text-accent underline" href="https://zenodo.org/records/4010759" target="_blank" rel="noreferrer noopener">
          zenodo.org/records/4010759
        </a>
        ). INCLUDE-derived material is shared for <strong className="text-ink">non-commercial use only</strong> under{" "}
        <a className="font-bold text-accent underline" href="https://creativecommons.org/licenses/by-nc-sa/4.0/" target="_blank" rel="noreferrer noopener">
          CC BY-NC-SA 4.0
        </a>{" "}
        with attribution. Results are on the authors&apos; predefined split; signer independence is not verified.
      </p>
      <p className="mt-2">Your camera video stays in your browser; only hand and body landmarks are sent to the server, and nothing is stored.</p>
    </footer>
  );
}
