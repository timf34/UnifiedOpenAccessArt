<script lang="ts">
	import { onMount } from 'svelte';
	import Gallery from '$lib/Gallery.svelte';
	import ArtistSelect from '$lib/ArtistSelect.svelte';

	let artworks: any[] = [];
	let total = 0;
	let page = 1;
	let limit = 20;
	let search = '';
	let selectedArtist = '';

	let loading = false;
	let errorMessage = '';

	const BASE_URL = 'http://127.0.0.1:8000';

	async function loadData() {
		loading = true;
		errorMessage = '';
		const searchTerm = selectedArtist || search;
		const url = `${BASE_URL}/api/artworks?search=${encodeURIComponent(searchTerm)}&page=${page}&limit=${limit}`;

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

	function handleSearch() {
		selectedArtist = ''; // Clear artist selection when searching
		page = 1; // reset to first page
		loadData();
	}

	function handleArtistSelect(artist: string) {
		selectedArtist = artist;
		search = ''; // Clear search when selecting artist
		page = 1;
		loadData();
	}
</script>

<div class="p-4 flex items-center justify-between">
	<div class="flex gap-2 items-center flex-wrap">
		<h1 class="text-2xl font-bold">Artworks Gallery</h1>

		<ArtistSelect 
			{selectedArtist}
			onSelect={handleArtistSelect}
		/>

		<div class="h-6 border-l border-gray-300 mx-2"></div>

		<!-- Search input -->
		<input
			type="text"
			bind:value={search}
			placeholder="Search artworks..."
			class="border px-2 py-1 rounded"
		/>
		<button
			on:click={handleSearch}
			class="px-3 py-1 bg-gray-300 hover:bg-gray-400 rounded"
		>
			Search
		</button>
	</div>

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

<!-- States -->
{#if loading}
	<p class="p-4">Loading...</p>
{:else if errorMessage}
	<p class="p-4 text-red-500">{errorMessage}</p>
{:else}
	<Gallery {artworks} />
{/if}

<div class="p-4 text-sm text-gray-600">
	Page {page} out of {Math.ceil(total / limit)}
	({total} total artworks)
</div>
