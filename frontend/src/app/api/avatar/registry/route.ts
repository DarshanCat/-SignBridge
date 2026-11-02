import { NextResponse } from "next/server";
import signRegistry from "@/config/sign_registry.json";

export async function GET() {
  return NextResponse.json(signRegistry);
}
