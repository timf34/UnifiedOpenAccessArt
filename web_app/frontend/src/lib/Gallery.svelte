<script lang="ts">
    export let artworks: any[] = [];
</script>

<div class="columns-1 sm:columns-2 md:columns-3 lg:columns-4 xl:columns-5 gap-4 space-y-4 p-4">
    {#each artworks as art}
        <a
                href={`/artworks/${art.id}`}
                class="break-inside-avoid overflow-hidden rounded shadow bg-white mb-4 block no-underline hover:shadow-lg transition-shadow"
        >
            {#if art.image_url}
                <img
                        src={art.image_url}
                        alt={art.title}
                        class="w-full object-cover"
                        loading="lazy"
                />
            {:else}
                <div class="bg-gray-200 aspect-[4/3] flex items-center justify-center">
                    <p class="text-gray-500 text-sm">No image</p>
                </div>
            {/if}
            <div class="p-3">
                <h2 class="text-lg font-semibold truncate text-black">{art.title}</h2>
                <p class="text-sm text-gray-700">{art.artist_name}</p>
                <p class="text-xs text-gray-500 mt-1">{art.museum}</p>
            </div>
        </a>
    {/each}
</div>
