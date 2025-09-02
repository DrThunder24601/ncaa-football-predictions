import { NextResponse } from 'next/server';

export async function GET() {
  return NextResponse.json({
    message: "API is working",
    envVars: {
      hasPrivateKey: !!process.env.GOOGLE_PRIVATE_KEY,
      hasClientEmail: !!process.env.GOOGLE_CLIENT_EMAIL,
      privateKeyLength: process.env.GOOGLE_PRIVATE_KEY?.length || 0,
      clientEmail: process.env.GOOGLE_CLIENT_EMAIL || 'not set'
    }
  });
}