<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';

	// Track local state
	let artworks: any[] = [];
	let total = 0;

	let page = 1;   // current page
	let limit = 5;  // how many items per page

	let loading = false;
	let errorMessage = '';

    const BASE_URL = 'http://127.0.0.1:8000';

	// We'll load data with a function (could also use SvelteKit's load()
	// in a +page.ts, but here's a straightforward approach).
	async function loadData() {
		loading = true;
		errorMessage = '';
		try {
			const res = await fetch(`${BASE_URL}/api/artworks?page=${page}&limit=${limit}`);
			if (!res.ok) {
				throw new Error(`Server responded with ${res.status} ${res.statusText}`);
			}
			const data = await res.json();
			artworks = data.artworks; // array
			total = data.total;       // total count of rows
		} catch (err: any) {
			errorMessage = err.message;
		} finally {
			loading = false;
		}
	}

	// Load first page on mount
	onMount(() => {
		loadData();
	});

	function nextPage() {
		if (page * limit < total) {
			page++;
			loadData();
		}
	}

	function prevPage() {
		if (page > 1) {
			page--;
			loadData();
		}
	}
</script>

<h1 class="text-2xl font-bold mb-4">Simple Artwork Gallery</h1>

{#if loading}
	<p>Loading data...</p>
{:else if errorMessage}
	<p class="text-red-500">{errorMessage}</p>
{:else if artworks?.length > 0}
	<div class="flex flex-col gap-2">
		{#each artworks as art}
			<div class="border p-2">
				<!-- Artwork info -->
				<h2 class="font-semibold">{art.title}</h2>
				<p>by {art.artist_name} @ {art.museum}</p>
				{#if art.image_url}
					<img src={art.image_url} alt={art.title} style="max-width:200px;" />
				{/if}
			</div>
		{/each}
	</div>

	<!-- Pagination controls -->
	<div class="mt-4">
		<p>Showing page {page}. Total artworks: {total}.</p>
		<button on:click={prevPage} disabled={page <= 1}>Previous</button>
		<button on:click={nextPage} disabled={page * limit >= total}>Next</button>
	</div>
{:else}
	<p>No artworks found.</p>
{/if}
