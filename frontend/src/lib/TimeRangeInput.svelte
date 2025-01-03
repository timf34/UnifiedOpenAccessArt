<script lang="ts">
    import { onMount } from 'svelte';
    
    export let onRangeChange: (range: { 
        min: number | null; 
        max: number | null; 
        min_is_bce: boolean;
        max_is_bce: boolean;
    }) => void;
    
    const BASE_URL = 'http://127.0.0.1:8000';
    let minYear: number;
    let maxYear: number;
    let selectedMin: string = '';
    let selectedMax: string = '';
    let minIsBCE = false;
    let maxIsBCE = false;
    let loading = false;
    let error = '';

    async function loadTimeRange() {
        loading = true;
        error = '';
        try {
            const res = await fetch(`${BASE_URL}/api/time-range`);
            if (!res.ok) {
                throw new Error(`Failed to load time range: ${res.status}`);
            }
            const data = await res.json();
            minYear = data.min_year;
            maxYear = data.max_year;
        } catch (err: any) {
            error = err.message;
            console.error('Failed to load time range:', err);
        } finally {
            loading = false;
        }
    }

    function handleInput() {
        const min = selectedMin ? parseInt(selectedMin) : null;
        const max = selectedMax ? parseInt(selectedMax) : null;

        // Validate inputs
        if (min && min < 0 || max && max < 0) {
            error = 'Please use positive numbers and the BCE checkbox';
            return;
        }

        // Compare dates considering BCE
        if (min !== null && max !== null) {
            const minValue = minIsBCE ? -min : min;
            const maxValue = maxIsBCE ? -max : max;
            if (minValue > maxValue) {
                error = 'Start date must be before end date';
                return;
            }
        }

        error = '';
        onRangeChange({ 
            min, 
            max, 
            min_is_bce: minIsBCE,
            max_is_bce: maxIsBCE
        });
    }

    function formatPlaceholder(type: 'start' | 'end') {
        if (!minYear || !maxYear) return type === 'start' ? 'Start year' : 'End year';
        return type === 'start' ? 
            `e.g., ${minIsBCE ? '3000' : minYear}` : 
            `e.g., ${maxIsBCE ? '1000' : maxYear}`;
    }

    onMount(loadTimeRange);
</script>

<div class="w-full space-y-2">
    <label class="block text-sm font-medium text-slate-700">Time Period</label>
    
    {#if loading}
        <div class="h-[42px] flex items-center justify-center">
            <div class="w-6 h-6 border-2 border-slate-300 border-t-blue-500 rounded-full animate-spin"></div>
        </div>
    {:else}
        <div class="space-y-4">
            <!-- Start year -->
            <div class="flex gap-4 items-start">
                <div class="flex-1">
                    <label class="block text-sm text-slate-600 mb-1">Start Year</label>
                    <input
                        type="number"
                        bind:value={selectedMin}
                        on:input={handleInput}
                        placeholder={formatPlaceholder('start')}
                        min="0"
                        class="w-full pl-4 pr-4 py-2 rounded-lg border border-slate-200 
                            bg-white text-slate-700
                            focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-400
                            placeholder-slate-400 transition-all duration-200
                            {error ? 'border-red-300 focus:border-red-400 focus:ring-red-100' : ''}"
                    />
                </div>
                <label class="flex items-center gap-2 text-sm text-slate-600 pt-7">
                    <input
                        type="checkbox"
                        bind:checked={minIsBCE}
                        on:change={handleInput}
                        class="rounded border-slate-300 text-blue-500 focus:ring-blue-200"
                    />
                    BCE
                </label>
            </div>

            <!-- End year -->
            <div class="flex gap-4 items-start">
                <div class="flex-1">
                    <label class="block text-sm text-slate-600 mb-1">End Year</label>
                    <input
                        type="number"
                        bind:value={selectedMax}
                        on:input={handleInput}
                        placeholder={formatPlaceholder('end')}
                        min="0"
                        class="w-full pl-4 pr-4 py-2 rounded-lg border border-slate-200 
                            bg-white text-slate-700
                            focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-400
                            placeholder-slate-400 transition-all duration-200
                            {error ? 'border-red-300 focus:border-red-400 focus:ring-red-100' : ''}"
                    />
                </div>
                <label class="flex items-center gap-2 text-sm text-slate-600 pt-7">
                    <input
                        type="checkbox"
                        bind:checked={maxIsBCE}
                        on:change={handleInput}
                        class="rounded border-slate-300 text-blue-500 focus:ring-blue-200"
                    />
                    BCE
                </label>
            </div>
        </div>

        {#if error}
            <p class="text-red-500 text-sm mt-1">
                {error}
            </p>
        {/if}
    {/if}
</div> 