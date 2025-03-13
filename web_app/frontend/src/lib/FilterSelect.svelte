<script lang="ts">
    import { onMount } from 'svelte';

    export let value = '';
    export let onSelect: (value: string) => void;
    export let endpoint: string;
    export let label: string;
    export let placeholder = 'All';
    
    const BASE_URL = 'http://127.0.0.1:8000';
    let items: { name: string; count: number }[] = [];
    let loading = false;
    let error = '';

    async function loadItems() {
        loading = true;
        error = '';
        try {
            const res = await fetch(`${BASE_URL}/api/${endpoint}`);
            if (!res.ok) {
                throw new Error(`Failed to load ${label}: ${res.status}`);
            }
            items = await res.json();
        } catch (err: any) {
            error = err.message;
            console.error(`Failed to load ${label}:`, err);
        } finally {
            loading = false;
        }
    }

    function handleSelect() {
        onSelect(value);
    }

    onMount(loadItems);
</script>

<div class="relative w-full">
    <label class="block text-sm font-medium text-slate-700 mb-1">
        {label}
    </label>
    <div class="relative">
        <select
            bind:value
            on:change={handleSelect}
            class="w-full appearance-none pl-4 pr-10 py-2 rounded-lg border border-slate-200 
                bg-white text-slate-700
                focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-400
                disabled:bg-slate-50 disabled:cursor-wait
                {error ? 'border-red-300 focus:border-red-400 focus:ring-red-100' : ''}
                transition-all duration-200"
            disabled={loading}
            style="z-index: 30;"
        >
            <option value="">{placeholder}</option>
            {#each items as item}
                <option value={item.name} class="py-1">
                    {item.name} ({item.count})
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