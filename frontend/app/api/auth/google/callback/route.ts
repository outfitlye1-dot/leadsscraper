import { NextRequest, NextResponse } from "next/server";

/**
 * Google OAuth hits this URL when a Vercel callback is still registered.
 * Forward the code/state to FastAPI on Railway, which exchanges the token.
 */
export async function GET(request: NextRequest) {
  const apiBase = (process.env.NEXT_PUBLIC_API_URL || "").replace(/\/$/, "");
  if (!apiBase.startsWith("http")) {
    return NextResponse.redirect(new URL("/login?error=Google+callback+not+configured", request.url));
  }
  const dest = `${apiBase}/auth/google/callback${request.nextUrl.search}`;
  return NextResponse.redirect(dest);
}
