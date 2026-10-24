import { NextRequest, NextResponse } from 'next/server';
const allowed = /^(health|metadata|locations\/autocomplete|journey\/(route|recommendations)|chargers(?:\/[^/]+(?:\/history)?)?)$/;
export async function GET(request: NextRequest, context: {params: Promise<{path: string[]}>}) {
  const {path} = await context.params;
  const route = path.join('/');
  if (!allowed.test(route)) return NextResponse.json({detail: 'Not found'}, {status:404});
  try {
    const upstream = new URL(`/api/${path.map(encodeURIComponent).join('/')}`, process.env.BACKEND_API_URL || 'http://127.0.0.1:8000');
    upstream.search = request.nextUrl.search;
    const response = await fetch(upstream, {cache:'no-store', signal:AbortSignal.timeout(120000)});
    const body = await response.json();
    return NextResponse.json(body, {status:response.status});
  } catch { return NextResponse.json({detail:'The ChargeSmart backend is unreachable. Start the API and check BACKEND_API_URL.'}, {status:502}); }
}
