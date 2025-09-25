import type { APIRoute } from 'astro';
    
export const GET: APIRoute = async () => {
  // It's best practice to store the deploy hook URL in an environment variable
  const deployHookUrl = import.meta.env.VERCEL_DEPLOY_HOOK;

  if (!deployHookUrl) {
    return new Response(JSON.stringify({ message: "Deploy hook URL not configured" }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  try {
    const response = await fetch(deployHookUrl, { method: 'POST' });
    if (!response.ok) {
      throw new Error(`Deploy hook failed with status: ${response.status}`);
    }
    const data = await response.json();
    console.log('Vercel deploy hook triggered successfully:', data);

    return new Response(JSON.stringify({ message: "Build triggered" }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });

  } catch (error: any) {
    console.error('Error triggering Vercel deploy hook:', error.message);
    return new Response(JSON.stringify({ message: `Error: ${error.message}` }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
};