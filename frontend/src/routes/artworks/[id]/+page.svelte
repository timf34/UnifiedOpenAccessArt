<!-- src/routes/artworks/[id]/+page.svelte -->
<script lang="ts">
    export let data: { artwork: any };
    $: artwork = data?.artwork;
    $: hasArtwork = !!artwork;
</script>

<div class="p-4">
    <a
            href="/"
            class="text-blue-600 hover:underline inline-block mb-4"
    >
        ← Back to Gallery
    </a>

    {#if !hasArtwork}
        <div class="text-red-600 p-4 bg-red-100 rounded">
            Error: Artwork not found or failed to load
        </div>
    {:else}
        <div class="flex flex-col md:flex-row gap-4">
            <!-- Left side: large image or fallback -->
            <div class="flex-1">
                {#if artwork.image_url}
                    <img
                            src={artwork.image_url}
                            alt={artwork.title}
                            class="w-full object-cover rounded shadow"
                            loading="lazy"
                    />
                {:else}
                    <div class="bg-gray-200 h-64 flex items-center justify-center rounded shadow">
                        <p class="text-gray-500">No Image Available</p>
                    </div>
                {/if}
            </div>

            <!-- Right side: metadata -->
            <div class="flex-1 space-y-2">
                <h1 class="text-2xl font-bold">{artwork.title}</h1>
                <p class="text-gray-700 italic">{artwork.type}</p>

                <div class="text-sm text-gray-600">
                    <p><strong>Museum:</strong> {artwork.museum}</p>
                    <p><strong>Artist:</strong> {artwork.artist_name}</p>

                    {#if artwork.artist_birth || artwork.artist_death}
                        <p>
                            <strong>Artist Lifespan:</strong>
                            {artwork.artist_birth ? artwork.artist_birth : 'unknown'} –
                            {artwork.artist_death ? artwork.artist_death : 'unknown'}
                        </p>
                    {/if}

                    {#if artwork.date_text}
                        <p><strong>Date:</strong> {artwork.date_text}</p>
                    {/if}

                    {#if artwork.url}
                        <p>
                            <a
                                    href={artwork.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    class="text-blue-600 hover:underline"
                            >
                                View Original Source
                            </a>
                        </p>
                    {/if}
                </div>
            </div>
        </div>
    {/if}
</div>
