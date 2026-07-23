export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    if (url.pathname.startsWith('/api/')) {
      return new Response(JSON.stringify({ status: 'error', message: 'API nog niet geimplementeerd (volgt in Fase 3).' }), {
        status: 501,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    // Alles wat geen /api/ is: gewoon de statische site serveren
    return env.ASSETS.fetch(request);
  }
};
