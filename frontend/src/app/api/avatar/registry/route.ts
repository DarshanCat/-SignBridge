import { NextResponse } from "next/server";
import signRegistry from "../../../../config/sign_registry.json";
import { listClipFiles } from "../../../../lib/clipFiles";
import { computeRegistry, type RawSign } from "../../../../lib/registryReport";

export async function GET() {
  try {
    return NextResponse.json(computeRegistry((signRegistry?.signs ?? []) as RawSign[], listClipFiles()));
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ detail: msg }, { status: 500 });
  }
}
