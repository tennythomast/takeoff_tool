// src/app/api/health/route.ts
import { NextResponse } from 'next/server';

/**
 * Health check endpoint for the frontend service.
 * This is used by Docker to verify that the container is running and healthy.
 * It must return a 200 OK response.
 */
export async function GET() {
  return NextResponse.json({ status: 'ok' }, { status: 200 });
}

