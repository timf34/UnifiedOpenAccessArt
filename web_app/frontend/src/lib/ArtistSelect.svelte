<script lang="ts">
    import { onMount } from 'svelte';

    export let selectedArtist = '';
    export let onSelect: (artist: string) => void;
    
    const BASE_URL = 'http://127.0.0.1:8000';
    let artists: { name: string; count: number }[] = [];
    let loading = false;
    let error = '';

    async function loadArtists() {
        loading = true;
        error = '';
        try {
            const res = await fetch(`${BASE_URL}/api/artists`);
            if (!res.ok) {
                throw new Error(`Failed to load artists: ${res.status}`);
            }
            artists = await res.json();
        } catch (err: any) {
            error = err.message;
            console.error('Failed to load artists:', err);
        } finally {
            loading = false;
        }
    }

    function handleSelect() {
        onSelect(selectedArtist);
    }

    onMount(loadArtists);
</script>

<div class="relative flex-1 sm:flex-none min-w-[220px]">
    <div class="relative">
        <select
            bind:value={selectedArtist}
            on:change={handleSelect}
            class="w-full appearance-none pl-4 pr-10 py-2 rounded-lg border border-slate-200 
                bg-white text-slate-700
                focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-400
                disabled:bg-slate-50 disabled:cursor-wait
                {error ? 'border-red-300 focus:border-red-400 focus:ring-red-100' : ''}
                transition-all duration-200"
            disabled={loading}
        >
            <option value="">All Artists</option>
            {#each artists as artist}
                <option value={artist.name} class="py-1">
                    {artist.name} ({artist.count} {artist.count === 1 ? 'artwork' : 'artworks'})
                </option>
            {/each}
        </select>

        <!-- Custom dropdown arrow -->
        <div class="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none">
            {#if loading}
                <div class="w-4 h-4 border-2 border-slate-300 border-t-blue-500 rounded-full animate-spin"></div>
            {:else}
                <svg class="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                </svg>
            {/if}
        </div>
    </div>

    {#if error}
        <p class="absolute text-red-500 text-sm mt-1">
            {error}
        </p>
    {/if}
</div> 