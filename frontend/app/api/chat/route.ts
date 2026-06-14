import { NextRequest } from 'next/server';
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';
export const runtime = 'nodejs';
export const maxDuration = 60;
export async function POST(req: NextRequest) {
  const body = await req.json();
  try {
    const response = await fetch(`${BACKEND_URL}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        // Secreto compartido: solo nuestro proxy puede llamar al backend público.
        ...(process.env.BACKEND_SHARED_SECRET
          ? { 'X-Internal-Secret': process.env.BACKEND_SHARED_SECRET }
          : {}),
      },
      body: JSON.stringify(body),
    });
    if (!response.ok) {
      console.error('chat backend error:', response.status, await response.text());
      return new Response('No se pudo procesar la solicitud. Intenta de nuevo.', {
        status: response.status,
        headers: { 'Content-Type': 'text/plain; charset=utf-8' },
      });
    }
    return new Response(response.body, {
      headers: { 'Content-Type': 'text/plain; charset=utf-8' },
    });
  } catch (e) {
    console.error('chat proxy error:', e instanceof Error ? e.message : String(e));
    return new Response('No se pudo conectar con el servidor. Intenta de nuevo.', {
      status: 502,
      headers: { 'Content-Type': 'text/plain; charset=utf-8' },
    });
  }
}
