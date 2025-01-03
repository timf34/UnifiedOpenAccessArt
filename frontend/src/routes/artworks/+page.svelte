// +page.ts
import type { PageLoad } from './$types';
import type { Artwork } from '$lib/types';

export const load = (async ({ fetch, url }) => {
  // For example, read a search param from the URL ?search=<query>
  // If none is provided, default to empty.
  const searchQuery = url.searchParams.get('search') ?? '';

  const apiUrl = `/api/artworks?search=${encodeURIComponent(searchQuery)}`;

  // SvelteKit best practice is to use the built-in `fetch` (not window.fetch)
  const response = await fetch(apiUrl);
  const artworks: Artwork[] = await response.json();

  return {
    artworks,
    searchQuery
  };
}) satisfies PageLoad;
