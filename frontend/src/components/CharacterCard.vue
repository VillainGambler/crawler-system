<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'

const socket = ref<WebSocket | null>(null)

// Add this near your other refs
const combatLog = ref<string[]>([])

const props = defineProps<{
  id: string
}>()

// --- DATA MODELS ---
interface Item {
  name: string
  type: string
  count?: number
}

interface Character {
  name: string
  race: string
  player_class: string
  level: number
  stats: {
    strength: number
    dexterity: number
    constitution: number
    intelligence: number
    charisma: number
  }
  // We explicitly add inventory here so TypeScript is happy
  inventory: Item[]
  equipment: Record<string, any>
}

// --- STATE ---
const character = ref<Character | null>(null)
const loading = ref(true)
const error = ref('')
const activeTab = ref('STATS') // <--- NEW: Tracks which tab is open

// --- ACTIONS ---
const tabs = ['STATS', 'INVENTORY', 'SKILLS']

async function fetchCharacter(charId: string) {
  loading.value = true
  error.value = ''
  character.value = null
  
  try {
    // SECURITY NOTE: Hardcoded IP for Phase 1. 
    // TODO: Move to .env file in Phase 2.
    const response = await fetch(`/character/${charId}`)
    
    if (!response.ok) throw new Error(`System AI Rejection: ${response.statusText}`)
    
    character.value = await response.json()
  } catch (err) {
    error.value = (err as Error).message
  } finally {
    loading.value = false
  }
}

async function adjustHP(amount: number) {
  if (!character.value) return

  // 1. Optimistic UI Update (Make it feel instant)
  character.value.hp.current += amount
  
  // 2. Send to Backend
  try {
    const response = await fetch(`/character/${props.id}/adjust-hp`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ amount: amount })
    })
    
    if (!response.ok) throw new Error("HP Update Failed")
    
    // Optional: Re-sync with server to be sure
    // fetchCharacter(props.id) 
  } catch (err) {
    console.error(err)
    // Rollback on error
    character.value.hp.current -= amount 
    alert("System Error: Could not sync HP")
  }
}

async function useItem(itemName: string) {
  if (!character.value) return
  
  // Optimistic UI: Find item locally and decrement it immediately
  const itemIndex = character.value.inventory.findIndex(i => i.name === itemName)
  if (itemIndex !== -1) {
    if (character.value.inventory[itemIndex].count > 1) {
      character.value.inventory[itemIndex].count--
    } else {
      character.value.inventory.splice(itemIndex, 1) // Remove from list
    }
  }

  // Send to Backend
  try {
    const response = await fetch(`/character/${props.id}/use-item`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ item_name: itemName })
    })
    
    if (!response.ok) throw new Error("Failed to use item")
    
    // Optional: Update with the server's truth
    // const updatedChar = await response.json()
    // character.value = updatedChar
    
  } catch (err) {
    alert("System Error: Could not consume item")
    // Note: To be perfect, we should revert the change here if it failed.
  }
}

function connectWebSocket(charId: string) {
  if (socket.value) socket.value.close()

  // 👇 DYNAMIC HOST: Connects to wherever the page is served from
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host // e.g. "192.168.50.146:8000"
  
  console.log(`Connecting to WebSocket for ${charId}...`)
  socket.value = new WebSocket(`${protocol}//${host}/ws/${charId}`)

  socket.value.onmessage = (event) => {
    const data = JSON.parse(event.data)
    
    if (data.type === 'HP_UPDATE') {
       if (character.value) character.value.hp = data.new_hp
    } 
    else if (data.type === 'FULL_REFRESH') {
       fetchCharacter(charId)
    } 
    else if (data.type === 'LOG') {
       // Add new message to the TOP of the list
       combatLog.value.unshift(data.message)
       
       // Optional: Keep list short (max 20 items)
       if (combatLog.value.length > 20) combatLog.value.pop()
    }
  }

  socket.value.onopen = () => console.log("WebSocket Connected!")
  socket.value.onerror = (e) => console.error("WebSocket Error:", e)
}
// --- LIFECYCLE ---
onMounted(() => {
  fetchCharacter(props.id)
  connectWebSocket(props.id) // <--- Connect!
})

watch(() => props.id, (newId) => {
  fetchCharacter(newId)
  connectWebSocket(newId) // <--- Re-connect if ID changes!
})
</script>

<template>
  <div class="w-full max-w-md mx-auto bg-gray-950 rounded-xl border-2 border-green-800 shadow-[0_0_15px_rgba(34,197,94,0.3)] overflow-hidden flex flex-col h-[650px] relative">
    
    <div class="absolute inset-0 opacity-5 pointer-events-none" 
         style="background-image: radial-gradient(#22c55e 1px, transparent 1px); background-size: 20px 20px;">
    </div>

    <div v-if="character" class="relative z-10 p-4 bg-gray-900/90 border-b-2 border-green-800 flex justify-between items-end backdrop-blur-sm">
      <div>
        <h1 class="text-3xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-green-400 to-emerald-600 uppercase tracking-tighter filter drop-shadow-[0_0_5px_rgba(34,197,94,0.5)]">
          {{ character.name }}
        </h1>
        <div class="flex items-center gap-2 mt-1">
          <span class="bg-green-900/50 text-green-400 text-xs px-2 py-0.5 rounded border border-green-800">
            LVL {{ character.level }}
          </span>
          <span class="text-gray-400 text-xs uppercase tracking-widest">
            {{ character.race }} {{ character.player_class }}
          </span>
        </div>
      </div>
      <div class="text-right">
         <div class="text-[10px] text-green-600 uppercase animate-pulse">System ID</div>
         <div class="font-mono text-green-500 text-xs">{{ props.id }}</div>
      </div>
    </div>

    <div v-if="loading" class="flex-1 flex flex-col items-center justify-center text-green-500 space-y-4">
      <div class="w-12 h-12 border-4 border-green-500 border-t-transparent rounded-full animate-spin"></div>
      <div class="animate-pulse tracking-widest text-sm">ACCESSING MAINFRAME...</div>
    </div>

    <div v-else-if="error" class="p-6 m-4 bg-red-900/20 border-2 border-red-500 text-red-400 text-center shadow-[0_0_20px_rgba(239,68,68,0.2)]">
      <div class="text-4xl mb-2">⚠</div>
      <div class="font-bold">CONNECTION SEVERED</div>
      <div class="text-xs mt-2 opacity-75">{{ error }}</div>
    </div>

    <div v-else-if="character" class="relative z-10 flex-1 flex flex-col overflow-hidden">
      
      <div class="flex border-b-2 border-green-900 bg-gray-900/50">
        <button 
          v-for="tab in tabs" 
          :key="tab"
          @click="activeTab = tab"
          class="flex-1 py-3 text-sm font-bold tracking-[0.2em] transition-all relative overflow-hidden group"
          :class="activeTab === tab ? 'text-green-400 bg-green-900/20' : 'text-gray-600 hover:text-green-600'"
        >
          <div v-if="activeTab === tab" class="absolute bottom-0 left-0 w-full h-0.5 bg-green-400 shadow-[0_0_10px_#4ade80]"></div>
          {{ tab }}
        </button>
      </div>

      <div v-if="activeTab === 'STATS'" class="p-6 space-y-6 overflow-y-auto custom-scrollbar">
        
        <div class="bg-gray-900/80 p-4 rounded-lg border border-gray-800 shadow-inner relative overflow-hidden">
            
            <div class="absolute bottom-0 left-0 h-1 bg-red-900 w-full">
                <div class="h-full bg-red-500 transition-all duration-500" :style="`width: ${(character.hp.current / character.hp.max) * 100}%`"></div>
            </div>

            <div class="flex justify-between items-center relative z-10">
                <span class="text-red-500 font-bold tracking-widest text-sm">HP</span>
                
                <div class="flex items-center gap-4">
                    <button @click="adjustHP(-1)" class="w-8 h-8 rounded bg-gray-800 text-red-500 hover:bg-red-500 hover:text-white border border-red-900/50 transition-all active:scale-95 text-lg font-bold shadow-lg flex items-center justify-center">-</button>
                    
                    <div class="flex items-baseline gap-1 min-w-[80px] justify-center">
                        <span class="text-3xl font-mono font-bold" :class="character.hp.current < character.hp.max / 2 ? 'text-red-500 animate-pulse' : 'text-white'">
                          {{ character.hp.current }}
                        </span>
                        <span class="text-gray-600 text-sm font-mono">
                          /{{ character.hp.max }}
                        </span>
                    </div>

                    <button @click="adjustHP(1)" class="w-8 h-8 rounded bg-gray-800 text-green-500 hover:bg-green-500 hover:text-white border border-green-900/50 transition-all active:scale-95 text-lg font-bold shadow-lg flex items-center justify-center">+</button>
                </div>
            </div>
        </div>

      </div>

      <div v-if="activeTab === 'INVENTORY'" class="p-4 overflow-y-auto custom-scrollbar">
        
        <div class="grid grid-cols-2 gap-3 mb-6">
          <div v-for="(slot, name) in {Right: character.equipment.right_hand, Body: character.equipment.body}" :key="name"
               class="bg-gray-900/50 p-3 rounded border border-gray-700 flex flex-col items-center justify-center min-h-[5rem] relative group hover:border-green-500/50 transition-all">
            <span class="absolute top-1 left-2 text-[8px] text-gray-600 uppercase tracking-widest">{{ name }}</span>
            <span v-if="slot" class="text-green-300 font-bold text-center text-sm filter drop-shadow-[0_0_3px_rgba(74,222,128,0.5)]">{{ slot.name }}</span>
            <span v-else class="text-gray-800 text-2xl select-none">Empty</span>
          </div>
        </div>

        <h3 class="text-gray-500 text-[10px] uppercase tracking-[0.2em] mb-3 ml-1">Backpack Storage</h3>
        
        <div v-if="character.inventory.length > 0" class="space-y-2">
          <div v-for="(item, index) in character.inventory" :key="index" 
               class="flex justify-between items-center bg-gray-900 p-3 rounded border border-gray-800 hover:border-green-500/50 hover:bg-gray-800 transition-all group shadow-sm">
            <div>
              <div class="text-gray-300 font-bold group-hover:text-green-300 transition-colors">{{ item.name }}</div>
              <div class="text-[9px] text-gray-500 uppercase tracking-wider">{{ item.type }}</div>
            </div>
            <div class="flex items-center gap-3">
              <div class="text-lg font-mono text-gray-400">x{{ item.count }}</div>
              <button 
                @click="useItem(item.name)"
                class="bg-green-900/20 hover:bg-green-500 text-green-500 hover:text-white border border-green-900 text-[10px] font-bold py-1 px-3 rounded uppercase tracking-widest active:scale-95 transition-all shadow-[0_0_5px_rgba(34,197,94,0.1)] hover:shadow-[0_0_10px_rgba(34,197,94,0.5)]"
              >
                Use
              </button>
            </div>
          </div>
        </div>
        
        <div v-else class="text-center text-gray-700 py-8 border-2 border-dashed border-gray-800 rounded opacity-50">
          [ NO ITEMS DETECTED ]
        </div>
      </div>

      <div v-if="activeTab === 'SKILLS'" class="p-6 overflow-y-auto custom-scrollbar">
        <div class="grid grid-cols-1 gap-2">
          <div v-for="(level, skillName) in character.skills" :key="skillName" 
               class="flex justify-between items-center bg-gray-900/50 p-2 px-4 rounded border border-gray-800 hover:border-green-900 transition-colors">
             <span class="text-gray-400 capitalize text-sm">{{ skillName }}</span>
             <span class="text-green-400 font-mono text-lg font-bold">{{ level }}</span>
          </div>
        </div>
        <div class="mt-6 flex flex-wrap gap-2">
          <span v-for="feat in character.feats" :key="feat" 
                class="px-3 py-1 bg-green-900/10 text-green-400 text-xs rounded border border-green-900/30">
            {{ feat }}
          </span>
        </div>
      </div>

      <div class="bg-black border-t-2 border-green-900 p-3 h-48 flex flex-col font-mono relative">
        <div class="absolute inset-0 bg-gradient-to-b from-transparent to-green-900/5 pointer-events-none"></div>

        <h3 class="text-green-700 text-[9px] uppercase tracking-widest mb-2 flex items-center gap-2 z-10">
          <span class="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse shadow-[0_0_5px_#22c55e]"></span>
          System Log
        </h3>
        
        <div class="flex-1 overflow-y-auto space-y-1 text-xs z-10 custom-scrollbar pr-2">
          <div v-if="combatLog.length === 0" class="text-gray-800 italic">
            > Initialization Complete...
          </div>
          
          <div v-for="(log, index) in combatLog" :key="index" class="text-green-400/90 pl-2 border-l border-green-900/50 animate-in fade-in slide-in-from-left-2 duration-300">
            <span class="text-green-700 mr-2 opacity-50">></span>{{ log }}
          </div>
        </div>
      </div>

    </div>
  </div>
</template>