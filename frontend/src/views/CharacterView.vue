<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import CharacterCard from '../components/CharacterCard.vue'

const route = useRoute()
const characterId = ref('')

// We watch the URL. If it changes, we update our local variable.
// This is critical for switching characters without refreshing the page.
watch(
  () => route.params.id,
  (newId) => {
    characterId.value = newId as string
  },
  { immediate: true } // Run this logic immediately upon load
)
</script>

<template>
  <div class="min-h-screen flex flex-col items-center justify-center p-4">
    <CharacterCard :id="characterId" />
  </div>
</template>