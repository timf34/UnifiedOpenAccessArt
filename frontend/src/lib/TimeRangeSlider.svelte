<script lang="ts">
    import { onMount } from 'svelte';
    
    export let onRangeChange: (range: { min: number; max: number }) => void;
    
    const BASE_URL = 'http://127.0.0.1:8000';
    let minYear: number;
    let maxYear: number;
    let selectedMin: number;
    let selectedMax: number;
    let loading = false;
    let error = '';
    let isDragging = false;

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
            selectedMin = minYear;
            selectedMax = maxYear;
        } catch (err: any) {
            error = err.message;
            console.error('Failed to load time range:', err);
        } finally {
            loading = false;
        }
    }

    function handleMinChange(event: Event) {
        const value = parseInt((event.target as HTMLInputElement).value);
        selectedMin = Math.min(value, selectedMax - 1);
        if (!isDragging) {
            onRangeChange({ min: selectedMin, max: selectedMax });
        }
    }

    function handleMaxChange(event: Event) {
        const value = parseInt((event.target as HTMLInputElement).value);
        selectedMax = Math.max(value, selectedMin + 1);
        if (!isDragging) {
            onRangeChange({ min: selectedMin, max: selectedMax });
        }
    }

    function handleDragStart() {
        isDragging = true;
    }

    function handleDragEnd() {
        isDragging = false;
        onRangeChange({ min: selectedMin, max: selectedMax });
    }

    function getLeftPosition() {
        return ((selectedMin - minYear) / (maxYear - minYear)) * 100;
    }

    function getRightPosition() {
        return 100 - ((selectedMax - minYear) / (maxYear - minYear)) * 100;
    }

    onMount(loadTimeRange);
</script>

<div class="w-full space-y-2">
    <label class="block text-sm font-medium text-slate-700">Time Period</label>
    
    {#if loading}
        <div class="h-[72px] flex items-center justify-center">
            <div class="w-6 h-6 border-2 border-slate-300 border-t-blue-500 rounded-full animate-spin"></div>
        </div>
    {:else if error}
        <p class="text-red-500 text-sm">{error}</p>
    {:else}
        <div class="relative pt-2 pb-6">
            <!-- Range inputs -->
            <div class="relative h-2">
                <div class="absolute w-full h-2 bg-slate-200 rounded"></div>
                <div
                    class="absolute h-2 bg-blue-500 rounded"
                    style="left: {getLeftPosition()}%; right: {getRightPosition()}%"
                ></div>
                <input
                    type="range"
                    min={minYear}
                    max={maxYear}
                    bind:value={selectedMin}
                    on:input={handleMinChange}
                    on:mousedown={handleDragStart}
                    on:mouseup={handleDragEnd}
                    on:touchstart={handleDragStart}
                    on:touchend={handleDragEnd}
                    class="absolute w-full appearance-none bg-transparent pointer-events-none"
                    style="
                        --thumb-color: white;
                        --thumb-shadow: 0 0 0 4px rgba(59, 130, 246, 0.1);
                        --thumb-border: 2px solid rgb(59, 130, 246);
                        height: 2px;
                    "
                />
                <input
                    type="range"
                    min={minYear}
                    max={maxYear}
                    bind:value={selectedMax}
                    on:input={handleMaxChange}
                    on:mousedown={handleDragStart}
                    on:mouseup={handleDragEnd}
                    on:touchstart={handleDragStart}
                    on:touchend={handleDragEnd}
                    class="absolute w-full appearance-none bg-transparent pointer-events-none"
                    style="
                        --thumb-color: white;
                        --thumb-shadow: 0 0 0 4px rgba(59, 130, 246, 0.1);
                        --thumb-border: 2px solid rgb(59, 130, 246);
                        height: 2px;
                    "
                />
            </div>

            <!-- Year labels -->
            <div class="flex justify-between mt-6 text-sm text-slate-600">
                <div class="relative">
                    <span class="absolute -translate-x-1/2 whitespace-nowrap">
                        {selectedMin}
                    </span>
                </div>
                <div class="relative">
                    <span class="absolute -translate-x-1/2 whitespace-nowrap">
                        {selectedMax}
                    </span>
                </div>
            </div>
        </div>
    {/if}
</div>

<style>
    input[type="range"] {
        -webkit-appearance: none;
        background: transparent;
    }

    input[type="range"]::-webkit-slider-thumb {
        -webkit-appearance: none;
        height: 16px;
        width: 16px;
        border-radius: 50%;
        background: var(--thumb-color);
        border: var(--thumb-border);
        box-shadow: var(--thumb-shadow);
        cursor: pointer;
        pointer-events: auto;
        margin-top: -7px;
    }

    input[type="range"]::-moz-range-thumb {
        height: 16px;
        width: 16px;
        border-radius: 50%;
        background: var(--thumb-color);
        border: var(--thumb-border);
        box-shadow: var(--thumb-shadow);
        cursor: pointer;
        pointer-events: auto;
    }

    input[type="range"]:focus {
        outline: none;
    }
</style> 