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

<div class="min-h-screen bg-gradient-to-br from-slate-50 to-white">
	<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
		<!-- Header section with controls -->
		<div class="bg-white rounded-xl shadow-sm border border-slate-200/60 p-6 mb-8">
			<div class="flex flex-col sm:flex-row gap-6 items-start sm:items-center justify-between">
				<div class="flex-1 space-y-4 w-full sm:w-auto">
					<h1 class="text-2xl font-semibold bg-clip-text text-transparent bg-gradient-to-r from-slate-800 to-slate-600">
						Artworks Gallery
					</h1>

					<div class="flex flex-col sm:flex-row gap-4 items-start sm:items-center w-full">
						<ArtistSelect 
							{selectedArtist}
							onSelect={handleArtistSelect}
						/>

						<div class="hidden sm:block h-8 w-px bg-slate-200 mx-2"></div>

						<div class="flex gap-2 items-center flex-1 w-full sm:w-auto">
							<div class="relative flex-1">
								<input
									type="text"
									bind:value={search}
									placeholder="Search artworks..."
									class="w-full pl-4 pr-10 py-2 rounded-lg border border-slate-200 
										focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-400
										placeholder-slate-400 transition-all duration-200"
								/>
								<button
									on:click={handleSearch}
									class="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded-md
										text-slate-400 hover:text-slate-600 hover:bg-slate-50 transition-colors"
								>
									<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
									</svg>
								</button>
							</div>
						</div>
					</div>
				</div>

				<!-- Pagination controls -->
				<div class="flex gap-2 w-full sm:w-auto">
					<button
						on:click={prevPage}
						disabled={loading || page <= 1}
						class="flex-1 sm:flex-none px-4 py-2 rounded-lg border border-slate-200 
							enabled:hover:border-slate-300 enabled:hover:bg-slate-50
							disabled:opacity-50 disabled:cursor-not-allowed
							text-slate-600 text-sm font-medium transition-colors"
					>
						Previous
					</button>
					<button
						on:click={nextPage}
						disabled={loading || page * limit >= total}
						class="flex-1 sm:flex-none px-4 py-2 rounded-lg border border-slate-200 
							enabled:hover:border-slate-300 enabled:hover:bg-slate-50
							disabled:opacity-50 disabled:cursor-not-allowed
							text-slate-600 text-sm font-medium transition-colors"
					>
						Next
					</button>
				</div>
			</div>
		</div>

		<!-- Content section -->
		<div class="bg-white rounded-xl shadow-sm border border-slate-200/60 p-6">
			{#if loading}
				<div class="flex items-center justify-center py-12">
					<div class="w-6 h-6 border-2 border-slate-300 border-t-blue-500 rounded-full animate-spin"></div>
				</div>
			{:else if errorMessage}
				<div class="p-4 bg-red-50 rounded-lg text-red-600 text-sm">
					{errorMessage}
				</div>
			{:else}
				<Gallery {artworks} />
			{/if}

			<div class="mt-6 pt-6 border-t border-slate-100 text-sm text-slate-500 flex items-center justify-between">
				<span>
					Page {page} of {Math.ceil(total / limit)}
				</span>
				<span>
					{total} total artworks
				</span>
			</div>
		</div>
	</div>
</div>
