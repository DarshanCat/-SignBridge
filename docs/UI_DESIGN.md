# UI design: Sakura Daylight (2026-11-04)

The interface was redesigned around the anime avatar. Two directions were proposed (mockups in `docs/screenshots/ui_directions/`); the owner chose **A, Sakura Daylight**. Light mode is the default and the dark counterpart is **Sakura Dusk**. No recognition, clip or evaluation code changed.

## What changed

- **Avatar as the centre.** Where the avatar signs, it sits in a large rounded stage with a soft gradient, drifting petals (decoration only), badges at the top and an always visible caption card at the bottom (the sign now playing in large type, the sentence, a progress bar, and the honesty note).
  - Conversation: the stage is the hero on the left (sticky on wide screens), the chat and the camera are on the right.
  - English to Sign: the stage with the playback dock under it (Play or Pause, Replay sign, Restart all, Stop, a segmented speed control) and the input card beside it.
  - Sign to English: the camera on the left and the avatar as a listening partner on the right. It breathes and blinks but does not sign here, and its caption shows what the recognizer understood, labelled as possibly wrong.
  - Record sign: the preview of a retargeted take is shown on the same stage.
  - Landmark check is a diagnostic page: it has the new look but no avatar.
- **Shell.** Pill tabs (ARIA tabs pattern with arrow keys, Home and End), a theme toggle, a skip link, a status strip with a dot and words for every item, and the footer with the licence and honesty text.
- **Theme.** The system setting is followed until the visitor uses the toggle; the choice is saved in `localStorage` (a convenience only, the page works without it) and applied before the first paint. The 3D canvas is transparent, so the stage colours come from the same CSS variables in both themes.
- **Typography.** Zen Maru Gothic (headings, the gloss caption) and Nunito (text), both self-hosted through `@fontsource` packages, so no request goes to a font service.

## Colour tokens and contrast

Tokens are CSS variables in `frontend/src/app/globals.css` and Tailwind colours of the same names. Every pair below is checked by `python -I tools/ui/check_contrast.py` and by the unit test `frontend/src/lib/theme.test.ts` (they read the CSS, so the numbers cannot drift). WCAG 2.1 AA needs 4.5 for text and 3 for borders of controls and focus rings.

| Pair | Light | Dark |
|---|---|---|
| Body text on the page | 14.41 | 16.33 |
| Text on cards | 15.22 | 14.63 |
| Secondary text on cards | 7.68 | 9.77 |
| Primary button text on the accent | 5.50 | 9.14 |
| Accent used as text on cards | 5.50 | 8.55 |
| Input and button borders on cards | 4.11 | 5.53 |
| Focus ring on cards | 6.50 | 8.37 |
| Good, warning, error and info notices (lowest of the four) | 5.82 | 8.06 |
| Text on the caption glass over the stage (lowest) | 7.39 | 9.58 |

Light tokens: page `#FFF7F5`, card `#FFFFFF`, text `#2B2233`, secondary text `#5B4E68`, accent `#B8386B`, focus `#5B49C8`. Dark tokens: page `#17111F`, card `#231B2E`, text `#F7EEF9`, secondary text `#CFC2DA`, accent `#FF9DC0`, focus `#BBAEFF`.

## Accessibility

- **Contrast:** AA for all text and control borders in both themes (above).
- **Automated audit:** `tools/ui/a11y_audit.js` runs axe-core (WCAG 2.0 and 2.1 A and AA plus best practice) on every tab, in light and dark, at 1440 and 390 pixels wide: 20 combinations, 0 violations, and the page never scrolls sideways.
- **Keyboard:** the shortcuts are unchanged (P play or pause, A replay, U undo, C clear, S send, R record; they do not fire while typing). Tabs follow the ARIA pattern, the speed control is a radio group with arrow keys, a skip link is the first stop, and the focus ring is a 3 pixel line in the focus colour.
- **Captions always visible:** the stage caption shows the current sign and sentence at all times, with the status text (an `aria-live` region); the sign names are also in the gloss chips.
- **Colour is never the only signal:** status dots come with words, notices with text, the current sign with a ring and the caption.
- **Reduced motion:** with the system setting, animations and transitions are removed, the petals stop, and the avatar's decorative idle motion (breathing, weight shift, head drift) is off. The hands stay relaxed (a pose, not a movement), blinking stays because a still face looks wrong, and a sign the visitor starts plays normally.
- **Touch and phones:** controls are at least 44 pixels high (48 for buttons), fields are 16 pixels so phones do not zoom, the layout is one column under 1024 pixels with the stage first, and the tab bar scrolls sideways.

## Honesty labels (always visible)

- A "Clip not signer-reviewed" badge on every stage and in the caption of every playing sign.
- "Research prototype" in the header and the footer text: not a certified translation or interpreting service.
- The footer licence text (INCLUDE, non-commercial only, CC BY-NC-SA 4.0, attribution) and the note that the camera video stays in the browser.
- The note that the avatar's face, blinking and head movements are rule-based approximations, and the line that names the model in use.
- Recognition results are labelled as possibly wrong; clips with no signer review stay marked in the gloss chips and the vocabulary list.

## Files

`frontend/src/app/globals.css` (tokens, components, motion), `tailwind.config.ts`, `app/page.tsx` (shell), `components/ui/AvatarStage.tsx`, `components/ui/SpeedControl.tsx`, `components/ThemeToggle.tsx`, `components/StatusPanel.tsx`, `components/Footer.tsx`, and the panels. `tools/ui/` holds the contrast checker, the axe audit and the screenshot script. Before and after screenshots are in `docs/screenshots/ui_redesign/`.
