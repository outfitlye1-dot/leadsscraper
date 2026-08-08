import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
/** Allow longer than default rewrite proxy when hosted (local Node still respects AbortSignal). */
export const maxDuration = 60;

const BACKEND = process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8001";

export async function POST(req: NextRequest) {
  let body: string;
  try {
    body = await req.text();
  } catch {
    return NextResponse.json(
      {
        success: false,
        count: 0,
        total_estimated: 0,
        message: "Invalid request body",
        leads: [],
      },
      { status: 400 }
    );
  }

  try {
    const upstream = await fetch(`${BACKEND}/api/scraper/demo`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
      // Hard cap so Next never hangs into an opaque 500 rewrite timeout
      signal: AbortSignal.timeout(55_000),
    });
    const text = await upstream.text();
    return new NextResponse(text, {
      status: upstream.status,
      headers: {
        "Content-Type": upstream.headers.get("Content-Type") || "application/json",
      },
    });
  } catch (err) {
    const timedOut =
      err instanceof Error &&
      (err.name === "TimeoutError" || err.name === "AbortError" || /aborted|timeout/i.test(err.message));
    return NextResponse.json(
      {
        success: false,
        count: 0,
        total_estimated: 0,
        message: timedOut
          ? "Demo timed out. Try again, or create an account for full scrapes."
          : "Demo scrape unavailable right now. Please try again.",
        leads: [],
      },
      { status: 200 }
    );
  }
}
