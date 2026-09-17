/**
 * A narrow proxy from this app's own origin to the FastAPI service.
 *
 * It exists so the browser never talks to the API directly: no CORS to keep in
 * step, no API host baked into the client bundle, and the service can sit on a
 * private network in a real deployment. The allowlist keeps it from becoming a
 * general-purpose open proxy — only the accommodation endpoints pass through.
 */

import { NextRequest, NextResponse } from "next/server";

const API_BASE_URL = process.env.API_BASE_URL ?? "http://127.0.0.1:8000";

const ALLOWED_PATHS: Array<{ method: "GET" | "POST"; pattern: RegExp }> = [
  { method: "GET", pattern: /^accommodations$/ },
  { method: "GET", pattern: /^accommodations\/[A-Za-z0-9-]{1,36}$/ },
  { method: "POST", pattern: /^accommodations$/ },
];

function isAllowed(method: "GET" | "POST", path: string): boolean {
  return ALLOWED_PATHS.some(
    (route) => route.method === method && route.pattern.test(path),
  );
}

function unreachable(): NextResponse {
  return NextResponse.json(
    {
      error: {
        code: "api_unreachable",
        message: "The accommodation service is not responding.",
        hint: `Start the backend, then reload. Expected at ${API_BASE_URL}.`,
      },
    },
    { status: 502 },
  );
}

async function forward(
  request: NextRequest,
  method: "GET" | "POST",
  segments: string[],
): Promise<NextResponse> {
  const path = segments.join("/");
  if (!isAllowed(method, path)) {
    return NextResponse.json(
      { error: { code: "not_found", message: "Unknown endpoint.", hint: null } },
      { status: 404 },
    );
  }

  const target = new URL(`${API_BASE_URL}/${path}`);
  target.search = request.nextUrl.search;

  try {
    const response = await fetch(target, {
      method,
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: method === "POST" ? await request.text() : undefined,
      cache: "no-store",
    });
    // Pass the service's own status and body straight through: its error
    // envelope is already the one the UI knows how to render.
    return new NextResponse(await response.text(), {
      status: response.status,
      headers: { "Content-Type": "application/json" },
    });
  } catch {
    return unreachable();
  }
}

type RouteContext = { params: Promise<{ path: string[] }> };

export async function GET(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  return forward(request, "GET", path);
}

export async function POST(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  return forward(request, "POST", path);
}
