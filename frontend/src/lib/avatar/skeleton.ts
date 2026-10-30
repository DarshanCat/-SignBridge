import { BONES } from "./clip";
import type { RigNode } from "./rig";

/** Structural checks for a rig definition (root, parents, cycles, names). Returns human-readable problems; empty means valid. */
export function validateRig(rig: readonly RigNode[], required: readonly string[] = BONES): string[] {
  const problems: string[] = [];
  const names = rig.map((n) => n.name);
  const set = new Set(names);
  if (set.size !== names.length) problems.push("duplicate bone names");
  const roots = rig.filter((n) => n.parent === null);
  if (roots.length !== 1) problems.push(`expected exactly one root, found ${roots.length}`);
  for (const n of rig) if (n.parent !== null && !set.has(n.parent)) problems.push(`${n.name}: unknown parent ${n.parent}`);

  const children = new Map<string, string[]>();
  for (const n of rig) if (n.parent) children.set(n.parent, [...(children.get(n.parent) ?? []), n.name]);
  const seen = new Set<string>();
  const stack = roots.map((r) => r.name);
  while (stack.length) {
    const cur = stack.pop()!;
    if (seen.has(cur)) continue;
    seen.add(cur);
    stack.push(...(children.get(cur) ?? []));
  }
  const unreachable = names.filter((n) => !seen.has(n));
  if (unreachable.length) problems.push(`bones unreachable from the root (cycle or orphan): ${unreachable.join(", ")}`);
  for (const b of required) if (!set.has(b)) problems.push(`missing required bone ${b}`);
  return problems;
}

/**
 * Check the node names of an imported skeleton (for example a GLB) against the bones sign clips animate.
 * An imported model must expose every required bone under the same name (or be renamed before this check).
 */
export function validateSkeletonNames(
  nodeNames: readonly string[],
  required: readonly string[] = BONES,
): { missing: string[]; ok: boolean } {
  const have = new Set(nodeNames);
  const missing = required.filter((b) => !have.has(b));
  return { missing, ok: missing.length === 0 };
}
