import type { PageLoad } from './$types';

export const load = (async ({ fetch, params }) => {
    // `params.id` is the dynamic part of the route: /artworks/123 => id=123
    const artId = params.id;

    // If your backend is at http://127.0.0.1:8000:
    const BASE_URL = 'http://127.0.0.1:8000';

    const res = await fetch(`${BASE_URL}/api/artworks/${artId}`);
    if (!res.ok) {
        // In SvelteKit, you can throw an error or a redirect if 404, etc.
        // We'll just throw an error, which SvelteKit can catch.
        throw new Error(`Failed to fetch artwork: ${res.status} ${res.statusText}`);
    }

    const artwork = await res.json();
    return { artwork };
}) satisfies PageLoad;
