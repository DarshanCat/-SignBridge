import type { SignClip } from "./clip";

/**
 * Rig self-test motion: raises the right arm, waves the forearm and curls the fingers.
 * It exists only to show that the skeleton, clip sampling and player work. It is NOT an ISL sign
 * and is never offered as one.
 */
export const RIG_TEST_CLIP: SignClip = {
  gloss: "RIG-TEST",
  duration: 3,
  source: { author: "SignBridge project", license: "Project-original", description: "Rig self-test motion, not a sign" },
  tracks: [
    { bone: "upperArm_r", keyframes: [{ t: 0, rot: [0, 0, 0] }, { t: 0.6, rot: [-1.3, 0, -0.5] }, { t: 2.4, rot: [-1.3, 0, -0.5] }, { t: 3, rot: [0, 0, 0] }] },
    { bone: "foreArm_r", keyframes: [{ t: 0, rot: [0, 0, 0] }, { t: 0.6, rot: [-0.6, 0, 0] }, { t: 1.2, rot: [-0.6, 0, 0.5] }, { t: 1.8, rot: [-0.6, 0, -0.5] }, { t: 2.4, rot: [-0.6, 0, 0] }, { t: 3, rot: [0, 0, 0] }] },
    ...["thumb", "index", "middle", "ring", "pinky"].map((f) => ({
      bone: `hand_r.${f}`,
      keyframes: [{ t: 0, rot: [0, 0, 0] as [number, number, number] }, { t: 1.2, rot: [0, 0, 0] as [number, number, number] }, { t: 1.8, rot: [-1.2, 0, 0] as [number, number, number] }, { t: 2.4, rot: [0, 0, 0] as [number, number, number] }, { t: 3, rot: [0, 0, 0] as [number, number, number] }],
    })),
  ],
};
