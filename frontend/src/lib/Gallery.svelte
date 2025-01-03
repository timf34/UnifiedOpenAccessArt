<!-- src/lib/Gallery.svelte -->
<script lang="ts">
    // We'll receive an array of artworks from the parent.
    // Adjust the type to your actual Artwork model if you have it in $lib/types.
    export let artworks: any[] = [];
</script>

<!--
  The Tailwind classes:
    - columns-*  => sets how many columns in a multi-column layout
    - gap-4      => spacing horizontally between columns
    - space-y-4  => vertical spacing between items within columns
-->
<div class="columns-1 sm:columns-2 md:columns-3 lg:columns-4 xl:columns-5 gap-4 space-y-4 p-4">
    {#each artworks as art}
        <!-- Each artwork card -->
        <div class="break-inside-avoid overflow-hidden rounded shadow bg-white mb-4">
            {#if art.image_url}
                <img
                        src={art.image_url}
                        alt={art.title}
                        class="w-full object-cover"
                        loading="lazy"
                />
            {:else}
                <!-- Fallback if no image -->
                <div class="bg-gray-200 aspect-[4/3] flex items-center justify-center">
                    <p class="text-gray-500 text-sm">No image</p>
                </div>
            {/if}

            <!-- Info area -->
            <div class="p-3">
                <h2 class="text-lg font-semibold truncate">{art.title}</h2>
                <p class="text-sm text-gray-700">{art.artist_name}</p>
                <p class="text-xs text-gray-500 mt-1">{art.museum}</p>
            </div>
        </div>
    {/each}
</div>
