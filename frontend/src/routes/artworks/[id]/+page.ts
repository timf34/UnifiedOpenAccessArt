// src/routes/artworks/[id]/+page.ts
import type { PageLoad } from './$types';

export const load = (async ({ fetch, params }) => {
    const artId = params.id;
    const BASE_URL = 'http://127.0.0.1:8000';
    const url = `${BASE_URL}/api/artworks/${artId}`;
    
    console.log('Fetching artwork from:', url);
    
    try {
        const res = await fetch(url);
        console.log('Response status:', res.status);
        
        if (!res.ok) {
            console.error('Error response:', await res.text());
            throw new Error(`Failed to fetch artwork: ${res.status} ${res.statusText}`);
        }

        const artwork = await res.json();
        console.log('Received artwork:', artwork);
        
        if (!artwork) {
            throw new Error('No artwork data received');
        }
        
        return { artwork };
    } catch (error) {
        console.error('Failed to load artwork:', error);
        throw error;
    }
}) satisfies PageLoad;
