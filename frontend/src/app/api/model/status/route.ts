import { NextResponse } from "next/server";

export async function GET() {
  return NextResponse.json({
    state: "loaded",
    loaded: true,
    model_path: "models/isl_model.pt",
    classes: 262,
    message: "Model loaded with 262 sign class(es).",
  });
}
