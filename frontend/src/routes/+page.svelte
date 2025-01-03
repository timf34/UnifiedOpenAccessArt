<script lang="ts">
	import { onMount } from 'svelte';
	import Gallery from '$lib/Gallery.svelte';
	import FilterSelect from '$lib/FilterSelect.svelte';
	import TimeRangeInput from '$lib/TimeRangeInput.svelte';

	let artworks: any[] = [];
	let total = 0;
	let page = 1;
	let limit = 20;
	let search = '';
	let selectedArtist = '';
	let selectedMuseum = '';
	let selectedMinYear: number | null = null;
	let selectedMaxYear: number | null = null;
	let selectedMinIsBCE = false;
	let selectedMaxIsBCE = false;

	let loading = false;
	let errorMessage = '';

	const BASE_URL = 'http://127.0.0.1:8000';

	async function loadData() {
		loading = true;
		errorMessage = '';
		const searchTerms = [selectedArtist, selectedMuseum, search].filter(Boolean);
		const searchTerm = searchTerms.join(' ');
		
		const params = new URLSearchParams({
			search: searchTerm,
			page: page.toString(),
			limit: limit.toString()
		});

		if (selectedMinYear !== null) {
			params.append('min_year', selectedMinYear.toString());
			params.append('min_is_bce', selectedMinIsBCE.toString());
		}
		if (selectedMaxYear !== null) {
			params.append('max_year', selectedMaxYear.toString());
			params.append('max_is_bce', selectedMaxIsBCE.toString());
		}

		const url = `${BASE_URL}/api/artworks?${params.toString()}`;

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

	function handleTimeRangeChange(range: { 
		min: number | null; 
		max: number | null; 
		min_is_bce: boolean;
		max_is_bce: boolean;
	}) {
		selectedMinYear = range.min;
		selectedMaxYear = range.max;
		selectedMinIsBCE = range.min_is_bce;
		selectedMaxIsBCE = range.max_is_bce;
		page = 1;
		loadData();
	}

	function formatYear(year: number | null, isBCE: boolean): string {
		if (year === null) return '';
		return `${year} ${isBCE ? 'BCE' : 'CE'}`;
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
		selectedArtist = '';
		selectedMuseum = '';
		page = 1;
		loadData();
	}

	function handleFilterSelect(type: string, value: string) {
		if (type !== 'artist') selectedArtist = '';
		if (type !== 'museum') selectedMuseum = '';
		
		switch (type) {
			case 'artist':
				selectedArtist = value;
				break;
			case 'museum':
				selectedMuseum = value;
				break;
		}
		
		search = '';
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

					<div class="flex flex-col gap-6 w-full">
						<!-- Filter controls -->
						<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 w-full">
							<FilterSelect 
								endpoint="artists"
								label="Artists"
								placeholder="All Artists"
								value={selectedArtist}
								onSelect={(value) => handleFilterSelect('artist', value)}
							/>

							<FilterSelect 
								endpoint="museums"
								label="Museums"
								placeholder="All Museums"
								value={selectedMuseum}
								onSelect={(value) => handleFilterSelect('museum', value)}
							/>

							<TimeRangeInput onRangeChange={handleTimeRangeChange} />

							<div class="relative w-full lg:col-span-3">
								<label class="block text-sm font-medium text-slate-700 mb-1">
									Search
								</label>
								<div class="relative">
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

						<!-- Active filters -->
						{#if selectedArtist || selectedMuseum || selectedMinYear !== null}
							<div class="flex flex-wrap gap-2">
								{#if selectedArtist}
									<span class="inline-flex items-center px-3 py-1 rounded-full text-sm bg-blue-50 text-blue-700">
										Artist: {selectedArtist}
										<button
											on:click={() => handleFilterSelect('artist', '')}
											class="ml-2 hover:text-blue-900"
										>
											×
										</button>
									</span>
								{/if}
								{#if selectedMuseum}
									<span class="inline-flex items-center px-3 py-1 rounded-full text-sm bg-blue-50 text-blue-700">
										Museum: {selectedMuseum}
										<button
											on:click={() => handleFilterSelect('museum', '')}
											class="ml-2 hover:text-blue-900"
										>
											×
										</button>
									</span>
								{/if}
								{#if selectedMinYear !== null}
									<span class="inline-flex items-center px-3 py-1 rounded-full text-sm bg-blue-50 text-blue-700">
										Years: {formatYear(selectedMinYear, selectedMinIsBCE)} - {formatYear(selectedMaxYear, selectedMaxIsBCE)}
										<button
											on:click={() => {
												selectedMinYear = null;
												selectedMaxYear = null;
												selectedMinIsBCE = false;
												selectedMaxIsBCE = false;
												loadData();
											}}
											class="ml-2 hover:text-blue-900"
										>
											×
										</button>
									</span>
								{/if}
							</div>
						{/if}
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
