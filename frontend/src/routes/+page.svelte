<!-- src/routes/+page.svelte -->
<script lang="ts">
	import { onMount } from 'svelte';
	import Gallery from '$lib/Gallery.svelte';  // Import our new component

	let artworks: any[] = [];
	let total = 0;

	// Pagination
	let page = 1;
	let limit = 20;

	// Basic loading/error states
	let loading = false;
	let errorMessage = '';

	// Hardcode or store in env variable
	const BASE_URL = 'http://127.0.0.1:8000';

	async function loadData() {
		loading = true;
		errorMessage = '';

		const url = `${BASE_URL}/api/artworks?page=${page}&limit=${limit}`;
		try {
			const res = await fetch(url);
			if (!res.ok) {
				throw new Error(`Server responded with ${res.status} ${res.statusText}`);
			}
			const data = await res.json();

			artworks = data.artworks;
			total = data.total;
		} catch (err: any) {
			errorMessage = err.message;
		} finally {
			loading = false;
		}
	}

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

<!-- Search or heading row (optional) -->
<div class="p-4 flex items-center justify-between">
	<h1 class="text-2xl font-bold">Unified Art Gallery</h1>
	<!-- Pagination controls -->
	<div class="space-x-2">
		<button
				on:click={prevPage}
				disabled={loading || page <= 1}
				class="px-3 py-1 bg-gray-300 hover:bg-gray-400 disabled:bg-gray-200 rounded"
		>
			Prev
		</button>
		<button
				on:click={nextPage}
				disabled={loading || page * limit >= total}
				class="px-3 py-1 bg-gray-300 hover:bg-gray-400 disabled:bg-gray-200 rounded"
		>
			Next
		</button>
	</div>
</div>

<!-- Show errors/Loading states -->
{#if loading}
	<p class="p-4">Loading...</p>
{:else if errorMessage}
	<p class="p-4 text-red-500">{errorMessage}</p>
{:else}
	<Gallery {artworks} />
{/if}

<!-- Info about pagination -->
<div class="p-4 text-sm text-gray-600">
	Page {page} out of {Math.ceil(total / limit)}
	({total} total artworks)
</div>
