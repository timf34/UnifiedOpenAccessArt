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

<div class="relative">
    {#if loading}
        <div class="absolute right-2 top-1/2 -translate-y-1/2">
            <div class="w-4 h-4 border-2 border-gray-300 border-t-gray-600 rounded-full animate-spin"></div>
        </div>
    {/if}
    
    <select
        bind:value={selectedArtist}
        on:change={handleSelect}
        class="border px-2 py-1 rounded bg-white min-w-[200px] {error ? 'border-red-500' : ''}"
        disabled={loading}
    >
        <option value="">All Artists</option>
        {#each artists as artist}
            <option value={artist.name}>
                {artist.name} ({artist.count} {artist.count === 1 ? 'artwork' : 'artworks'})
            </option>
        {/each}
    </select>

    {#if error}
        <p class="text-red-500 text-sm mt-1">{error}</p>
    {/if}
</div> 