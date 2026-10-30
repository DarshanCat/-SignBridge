import { BONES } from "./clip";

/** Procedural humanoid skeleton (original geometry, no external assets). Units are metres; the signer faces +z. */
export type Shape =
  | { kind: "box"; size: [number, number, number] }
  | { kind: "sphere"; radius: number }
  | { kind: "capsule"; radius: number; length: number };

export interface RigNode {
  name: string;
  parent: string | null;
  offset: [number, number, number];
  shape?: Shape;
  shapeOffset?: [number, number, number];
}

const FINGERS: [string, number, number][] = [
  ["thumb", 0.05, -0.03],
  ["index", 0.03, -0.1],
  ["middle", 0.01, -0.1],
  ["ring", -0.01, -0.1],
  ["pinky", -0.03, -0.095],
];

function arm(side: "l" | "r"): RigNode[] {
  const m = side === "l" ? 1 : -1;
  const hand = `hand_${side}`;
  return [
    { name: `upperArm_${side}`, parent: "chest", offset: [0.26 * m, 0.2, 0], shape: { kind: "capsule", radius: 0.05, length: 0.26 }, shapeOffset: [0, -0.14, 0] },
    { name: `foreArm_${side}`, parent: `upperArm_${side}`, offset: [0, -0.28, 0], shape: { kind: "capsule", radius: 0.042, length: 0.24 }, shapeOffset: [0, -0.13, 0] },
    { name: hand, parent: `foreArm_${side}`, offset: [0, -0.26, 0], shape: { kind: "box", size: [0.09, 0.1, 0.03] }, shapeOffset: [0, -0.05, 0] },
    ...FINGERS.map(([f, x, y]): RigNode => ({
      name: `${hand}.${f}`,
      parent: hand,
      offset: [x * m, y, 0],
      shape: { kind: "capsule", radius: 0.011, length: 0.05 },
      shapeOffset: [0, -0.035, 0],
    })),
  ];
}

export const RIG: RigNode[] = [
  { name: "hips", parent: null, offset: [0, 1, 0], shape: { kind: "box", size: [0.32, 0.18, 0.2] } },
  { name: "spine", parent: "hips", offset: [0, 0.1, 0], shape: { kind: "box", size: [0.34, 0.25, 0.2] }, shapeOffset: [0, 0.12, 0] },
  { name: "chest", parent: "spine", offset: [0, 0.25, 0], shape: { kind: "box", size: [0.42, 0.3, 0.22] }, shapeOffset: [0, 0.1, 0] },
  { name: "neck", parent: "chest", offset: [0, 0.27, 0], shape: { kind: "capsule", radius: 0.045, length: 0.06 }, shapeOffset: [0, 0.04, 0] },
  { name: "head", parent: "neck", offset: [0, 0.1, 0], shape: { kind: "sphere", radius: 0.12 }, shapeOffset: [0, 0.12, 0] },
  ...arm("l"),
  ...arm("r"),
];

/** Every animatable bone must exist in the rig (checked by tests). */
export function missingBones(): string[] {
  const names = new Set(RIG.map((n) => n.name));
  return BONES.filter((b) => !names.has(b));
}
