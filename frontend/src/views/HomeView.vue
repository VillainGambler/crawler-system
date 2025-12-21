<script setup lang="ts">
import { RouterLink } from 'vue-router'

// Hardcoded list for now. In Phase 2, we will fetch this list from AWS.
const characters = [
  { id: 'carl_001', name: 'Carl', role: 'Tank / Explosives', image: '💣' },
  { id: 'donut_001', name: 'Princess Donut', role: 'Magic / Chaos', image: '🐈' }
]
</script>

<template>
  <div class="min-h-screen flex flex-col items-center justify-center p-4">
    <h1 class="text-3xl font-bold text-green-500 mb-8 tracking-widest uppercase glow">
      Select Crawler
    </h1>

    <div class="grid gap-6 w-full max-w-md">
      <RouterLink 
        v-for="char in characters" 
        :key="char.id"
        :to="`/character/${char.id}`"
        class="block p-6 bg-gray-800 border border-green-800 rounded-xl hover:bg-gray-700 hover:border-green-400 transition-all group"
      >
        <div class="flex items-center justify-between">
          <div>
            <div class="text-2xl mb-1 group-hover:text-white text-green-400 font-bold">
              {{ char.name }}
            </div>
            <div class="text-xs text-gray-500 uppercase tracking-wider">
              {{ char.role }}
            </div>
          </div>
          <div class="text-4xl">{{ char.image }}</div>
        </div>
      </RouterLink>
    </div>
  </div>
</template>

<style scoped>
.glow {
  text-shadow: 0 0 10px rgba(74, 222, 128, 0.5);
}
</style>