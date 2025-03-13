<!-- src/lib/SearchToggle.svelte -->
<script lang="ts">
    export let useSemanticSearch: boolean;
    export let onChange: (value: boolean) => void;
</script>

<div class="flex items-center gap-2">
    <label class="relative inline-flex items-center cursor-pointer">
        <input
            type="checkbox"
            bind:checked={useSemanticSearch}
            on:change={() => onChange(useSemanticSearch)}
            class="sr-only peer"
        />
        <div class="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4
            peer-focus:ring-blue-100 rounded-full peer
            peer-checked:after:translate-x-full peer-checked:after:border-white
            after:content-[''] after:absolute after:top-[2px] after:left-[2px]
            after:bg-white after:border-gray-300 after:border after:rounded-full
            after:h-5 after:w-5 after:transition-all
            peer-checked:bg-blue-500">
        </div>
        <span class="ml-2 text-sm font-medium text-gray-900">
            Semantic Search
        </span>
    </label>

    <button
        type="button"
        class="ml-1 text-gray-400 hover:text-gray-600"
        title="What's this?"
        on:click={() => alert('Semantic search uses AI to understand the meaning of your search terms, not just exact matches. It can find related artworks even if they don\'t contain your exact search words.')}
    >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
    </button>
</div>