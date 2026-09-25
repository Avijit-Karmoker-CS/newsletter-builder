import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const HOP_BY_HOP = new Set([
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailers",
  "transfer-encoding",
  "upgrade",
  "host",
  "content-length",
]);

function apiOrigin() {
  return (process.env.API_PROXY_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
}

async function proxy(request: NextRequest, path: string[]) {
  const incoming = new URL(request.url);
  const target = `${apiOrigin()}/${path.join("/")}${incoming.search}`;
  const headers = new Headers();
  request.headers.forEach((value, key) => {
    if (!HOP_BY_HOP.has(key.toLowerCase())) headers.set(key, value);
  });
  const init: RequestInit = {
    method: request.method,
    headers,
    redirect: "manual",
  };
  if (request.method !== "GET" && request.method !== "HEAD") {
    init.body = await request.arrayBuffer();
  }
  const upstream = await fetch(target, init);
  const response = new NextResponse(upstream.body, { status: upstream.status });
  upstream.headers.forEach((value, key) => {
    if (key.toLowerCase() === "set-cookie" || HOP_BY_HOP.has(key.toLowerCase())) return;
    response.headers.set(key, value);
  });
  const setCookies =
    typeof upstream.headers.getSetCookie === "function" ? upstream.headers.getSetCookie() : [];
  if (setCookies.length) {
    for (const cookie of setCookies) response.headers.append("set-cookie", cookie);
  } else {
    const single = upstream.headers.get("set-cookie");
    if (single) response.headers.append("set-cookie", single);
  }
  return response;
}

type Context = { params: Promise<{ path: string[] }> };

export async function GET(request: NextRequest, context: Context) {
  const { path } = await context.params;
  return proxy(request, path);
}

export async function POST(request: NextRequest, context: Context) {
  const { path } = await context.params;
  return proxy(request, path);
}

export async function PATCH(request: NextRequest, context: Context) {
  const { path } = await context.params;
  return proxy(request, path);
}

export async function PUT(request: NextRequest, context: Context) {
  const { path } = await context.params;
  return proxy(request, path);
}

export async function DELETE(request: NextRequest, context: Context) {
  const { path } = await context.params;
  return proxy(request, path);
}
