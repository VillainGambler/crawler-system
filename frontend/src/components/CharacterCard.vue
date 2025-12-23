<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { useRoute } from 'vue-router'

// --- INTERFACES ---
interface Item {
  name: string;
  type: string;
  count?: number;
  stats?: any;
}

interface Character {
  name: string;
  race: string;
  player_class: string;
  level: number;
  gold: number;
  hp: {
    current: number;
    max: number;
    temp: number;
  };
  stats: {
    strength: number;
    dexterity: number;
    constitution: number;
    intelligence: number;
    charisma: number;
  };
  skills: Record<string, number>;
  feats: string[];
  inventory: Item[];
  equipment: {
    right_hand?: Item | null;
    left_hand?: Item | null;
    body?: Item | null;
    head?: Item | null;
    feet?: Item | null;
    [key: string]: Item | null | undefined;
  };
}

// --- STATE ---
const route = useRoute()
const character = ref<Character | null>(null)
const socket = ref<WebSocket | null>(null)
const activeTab = ref('STATS') 
const combatLog = ref<string[]>([])
const selectedSkill = ref<{name: string, level: number, desc: string} | null>(null)

// Roll State
const rollResult = ref<{d20: number, mod: number, total: number, crit: boolean} | null>(null)
const isRolling = ref(false)

// --- SKILL LIBRARY ---
const skillLibrary: Record<string, string> = {
  "strength": "Raw physical power. Used for smashing things, carrying loot, and not getting crushed by falling rocks.",
  "dexterity": "Agility and hand-eye coordination. Critical for ranged weapons, dodging traps, and pickpocketing.",
  "constitution": "Health and stamina. Determines how much poison you can drink before you die.",
  "intelligence": "Book smarts and magic theory. Useful for deciphering runes and understanding complex traps.",
  "wisdom": "Perception and intuition. Spotting the goblin hiding in the bushes before he stabs you.",
  "charisma": "Force of personality. Convincing the shopkeeper to lower prices or the guard to look the other way.",
  "athletics": "Running, jumping, swimming, climbing. Cardio is Rule #1.",
  "acrobatics": "Balance and flips. Useful for walking on narrow ledges or escaping grapples.",
  "stealth": "The art of not being seen. If they can't see you, they can't kill you.",
  "perception": "Noticing details. Hidden doors, traps, and loot often require a keen eye.",
  "investigation": "Deducing how things work. Figuring out which lever opens the door and which one kills everyone.",
  "insight": "Reading people. Telling if someone is lying or just stupid.",
  "survival": "Tracking, hunting, and finding shelter. Not dying in the wilderness.",
  "intimidation": "Scaring people into doing what you want. Usually involves shouting and threatening violence.",
  "persuasion": "Talking people into doing what you want. Usually involves logic or flattery.",
  "deception": "Lying. Convincingly.",
  "medicine": "Patching up wounds. Knowing the difference between a healing herb and poison ivy.",
  "arcana": "Knowledge of magic, spells, and magical creatures.",
  "history": "Knowledge of past events, kingdoms, and lore.",
  "religion": "Knowledge of gods, cults, and religious rites.",
  "explosives": "The art of blowing shit up!"
}

// --- AUDIO SYSTEM ---
function playSystemSound(type: 'click' | 'success') {
  try {
    const AudioContext = window.AudioContext || (window as any).webkitAudioContext
    if (!AudioContext) return
    
    const ctx = new AudioContext()
    const osc = ctx.createOscillator()
    const gain = ctx.createGain()
    
    osc.connect(gain)
    gain.connect(ctx.destination)
    
    if (type === 'click') {
      osc.frequency.value = 800
      osc.type = 'square'
      gain.gain.setValueAtTime(0.05, ctx.currentTime)
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.1)
      osc.start()
      osc.stop(ctx.currentTime + 0.1)
    } else if (type === 'success') {
      osc.frequency.value = 1200
      osc.type = 'sine'
      gain.gain.setValueAtTime(0.05, ctx.currentTime)
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.3)
      osc.start()
      osc.stop(ctx.currentTime + 0.3)
    }
  } catch (e) {
    console.error("Audio Error:", e)
  }
}

// --- API & WEBSOCKET ---
async function fetchCharacter(charId: string) {
  try {
    const res = await fetch(`/character/${charId}`)
    const data = await res.json()
    character.value = data
  } catch (err) {
    console.error("Failed to load character", err)
  }
}

function connectWebSocket(charId: string) {
  if (socket.value) socket.value.close()
  
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host
  socket.value = new WebSocket(`${protocol}//${host}/ws/${charId}`)

  socket.value.onmessage = (event) => {
    const data = JSON.parse(event.data)
    
    if (data.type === "update") {
      character.value = data.payload
    } else if (data.type === "log") {
      combatLog.value.unshift(data.message)
      if (combatLog.value.length > 50) combatLog.value.pop()
    } else if (data.type === "roll_result") {
      // HANDLE ROLL RESULT
      isRolling.value = false
      rollResult.value = data.payload
      playSystemSound('success')
      
      // Auto-close popup after 4 seconds
      setTimeout(() => {
        rollResult.value = null
        selectedSkill.value = null 
      }, 4000)
    }
  }
}

// --- ACTIONS ---
async function adjustHP(amount: number) {
  if (!character.value) return
  // Optimistic UI update
  const newCurrent = character.value.hp.current + amount
  character.value.hp.current = Math.min(newCurrent, character.value.hp.max) 
  
  await fetch(`/character/${route.params.id}/adjust-hp?amount=${amount}`, { method: 'POST' })
}

async function useItem(itemIndex: number) {
  if (!character.value) return
  const item = character.value.inventory[itemIndex]

  // Optimistic Update
  if (item) {
     if (item.count && item.count > 1) {
       item.count--
     } else {
       character.value.inventory.splice(itemIndex, 1)
     }
  }

  await fetch(`/character/${route.params.id}/use-item?item_index=${itemIndex}`, { method: 'POST' })
}

// ROLL ACTION
async function performRoll() {
  if (!selectedSkill.value) return
  isRolling.value = true
  playSystemSound('click')
  
  try {
    await fetch(`/character/${route.params.id}/roll`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ skill_name: selectedSkill.value.name })
    })
  } catch (e) {
    console.error(e)
    isRolling.value = false
  }
}

function openSkillDetails(name: string, level: number) {
  const desc = skillLibrary[name.toLowerCase()] || "No data available in System Archives."
  selectedSkill.value = { name, level, desc }
}

// --- LIFECYCLE ---
onMounted(() => {
  const charId = route.params.id as string
  fetchCharacter(charId)
  connectWebSocket(charId)
})

onUnmounted(() => {
  if (socket.value) socket.value.close()
})

watch(() => route.params.id, (newId) => {
  fetchCharacter(newId as string)
  connectWebSocket(newId as string)
})
</script>

<template>
  <div v-if="character" class="min-h-screen bg-black text-green-500 font-mono p-4 flex flex-col max-w-lg mx-auto relative overflow-hidden">
    
    <div class="pointer-events-none fixed inset-0 z-50 bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.25)_50%),linear-gradient(90deg,rgba(255,0,0,0.06),rgba(0,255,0,0.02),rgba(0,0,255,0.06))] bg-[length:100%_4px,3px_100%] pointer-events-none"></div>

    <header class="border-b-2 border-green-700 pb-4 mb-4 relative">
      <div class="flex justify-between items-end">
        <div>
          <h1 class="text-4xl font-bold uppercase tracking-widest text-white drop-shadow-[0_0_10px_rgba(74,222,128,0.7)]">{{ character.name }}</h1>
          <p class="text-xs text-green-400 mt-1">LVL {{ character.level }} {{ character.race }} {{ character.player_class }} | SYSTEM v2.0</p>
        </div>
        <div class="text-right">
          <div class="text-[10px] text-green-600 animate-pulse">● CONNECTED</div>
        </div>
      </div>
    </header>

    <div class="mb-6 space-y-3">
      <div class="relative h-12 bg-gray-900 border border-green-800 rounded overflow-hidden group">
        <div class="absolute inset-0 bg-red-900/20"></div>
        <div class="h-full bg-red-600 transition-all duration-500" :style="`width: ${(character.hp.current / character.hp.max) * 100}%`"></div>
        
        <div class="absolute inset-0 flex justify-between items-center px-4">
          <span class="text-xs font-bold text-red-300 uppercase tracking-widest">Health</span>
          <div class="flex items-baseline gap-1">
             <span class="text-3xl font-mono font-bold" :class="character.hp.current < character.hp.max / 2 ? 'text-red-500 animate-pulse' : 'text-white'">
                {{ character.hp.current }}
             </span>
             <span class="text-gray-400 text-sm">/{{ character.hp.max }}</span>
          </div>
        </div>
      </div>

      <div class="flex gap-2">
        <button @click="adjustHP(-1)" class="flex-1 bg-red-900/30 hover:bg-red-600 hover:text-white border border-red-800 text-red-500 py-3 rounded transition-all active:scale-95 font-bold uppercase tracking-wider text-sm">
          Take Hit
        </button>
        <button @click="adjustHP(1)" class="flex-1 bg-green-900/30 hover:bg-green-600 hover:text-black border border-green-800 text-green-500 py-3 rounded transition-all active:scale-95 font-bold uppercase tracking-wider text-sm">
          Heal
        </button>
      </div>
    </div>

    <nav class="flex border-b border-green-800 mb-4 text-sm overflow-x-auto">
      <button 
        v-for="tab in ['STATS', 'SKILLS', 'EQUIPMENT', 'INVENTORY', 'LOG']" 
        :key="tab"
        @click="activeTab = tab"
        class="px-4 py-2 hover:bg-green-900/30 transition-colors relative"
        :class="activeTab === tab ? 'text-white font-bold bg-green-900/20 border-b-2 border-green-500' : 'text-green-700'"
      >
        {{ tab }}
      </button>
    </nav>

    <main class="flex-1 overflow-hidden flex flex-col bg-gray-900/30 border border-green-900/50 rounded min-h-[300px]">
      
      <div v-if="activeTab === 'STATS'" class="p-6 grid grid-cols-2 gap-4">
        <div v-for="(val, stat) in character.stats" :key="stat" 
             class="bg-gray-900/80 p-3 rounded border border-gray-700 flex flex-col items-center justify-center aspect-square shadow-inner relative overflow-hidden group hover:border-green-500 transition-colors">
           <div class="text-[10px] uppercase text-gray-500 mb-1 tracking-widest group-hover:text-green-400 transition-colors">{{ stat }}</div>
           <div class="text-3xl font-bold text-white group-hover:scale-110 transition-transform">{{ val }}</div>
           <div class="absolute bottom-1 right-2 text-xs text-green-700 font-mono">{{ Math.floor((val - 10) / 2) >= 0 ? '+' : '' }}{{ Math.floor((val - 10) / 2) }}</div>
        </div>
      </div>

      <div v-if="activeTab === 'SKILLS'" class="p-6 overflow-y-auto custom-scrollbar relative">
        <div class="grid grid-cols-1 gap-2">
          <button 
            v-for="(level, skillName) in character.skills" 
            :key="skillName" 
            @click="openSkillDetails(String(skillName), level)"
            class="flex justify-between items-center bg-gray-900/50 p-2 px-4 rounded border border-gray-800 hover:border-green-500 hover:bg-green-900/20 transition-all cursor-pointer group text-left w-full"
          >
             <span class="text-gray-400 capitalize text-sm group-hover:text-green-400 transition-colors flex items-center gap-2">
               <span class="opacity-0 group-hover:opacity-100 text-[10px]">▶</span>
               {{ skillName }}
             </span>
             <span class="text-green-400 font-mono text-lg font-bold group-hover:shadow-[0_0_10px_rgba(74,222,128,0.5)] transition-all">{{ level }}</span>
          </button>
        </div>
        
        <div class="mt-6 flex flex-wrap gap-2">
          <span v-for="feat in character.feats" :key="feat" 
                class="px-3 py-1 bg-green-900/10 text-green-400 text-xs rounded border border-green-900/30">
            {{ feat }}
          </span>
        </div>
      </div>

      <div v-if="activeTab === 'EQUIPMENT'" class="p-6">
        <div class="grid grid-cols-2 gap-3 mb-6">
          <div v-for="(slot, name) in { 'Right Hand': character.equipment.right_hand, 'Body': character.equipment.body }" :key="name"
               class="bg-gray-900/50 p-3 rounded border border-gray-700 flex flex-col items-center justify-center min-h-[5rem] relative group hover:border-green-500/50 transition-all">
            <span class="absolute top-1 left-2 text-[8px] text-gray-600 uppercase tracking-widest">{{ name }}</span>
            <span v-if="slot && slot.name" class="text-green-300 font-bold text-center text-sm filter drop-shadow-[0_0_3px_rgba(74,222,128,0.5)]">
              {{ slot.name }}
            </span>
            <span v-else class="text-gray-800 text-2xl select-none">Empty</span>
          </div>
        </div>
      </div>

      <div v-if="activeTab === 'INVENTORY'" class="p-4 overflow-y-auto custom-scrollbar">
        <div class="flex justify-between items-center bg-yellow-900/20 border border-yellow-700/50 p-3 rounded mb-4">
          <span class="text-yellow-600 text-xs uppercase tracking-widest">Current Funds</span>
          <span class="text-yellow-400 font-bold text-xl drop-shadow-[0_0_5px_rgba(234,179,8,0.5)]">
            {{ character.gold }} <span class="text-xs">GP</span>
          </span>
        </div>

        <ul class="space-y-2">
           <li v-for="(item, index) in character.inventory" :key="index" class="flex justify-between items-center bg-gray-900/40 p-3 rounded border border-green-900/30 hover:bg-green-900/10 transition-colors">
              <div>
                <span class="text-white font-bold">{{ item.name }}</span>
                <span v-if="item.count && item.count > 1" class="ml-2 text-xs bg-green-900 text-green-300 px-1 rounded">x{{ item.count }}</span>
                <div class="text-[10px] text-green-700 uppercase">{{ item.type }}</div>
              </div>
              <button @click="useItem(index)" class="text-xs bg-green-800/20 hover:bg-green-500 hover:text-black border border-green-700 text-green-400 px-3 py-1 rounded transition-colors uppercase tracking-wider">
                Use
              </button>
           </li>
        </ul>
      </div>

      <div v-if="activeTab === 'LOG'" class="p-4 h-full overflow-y-auto custom-scrollbar font-mono text-xs space-y-1">
        <div v-for="(log, i) in combatLog" :key="i" class="border-l-2 border-green-800 pl-2 py-1 opacity-80 hover:opacity-100 hover:bg-green-900/10 transition-opacity">
          <span class="text-green-500">></span> {{ log }}
        </div>
      </div>

    </main>

    <footer class="mt-4 text-center text-[10px] text-green-800 uppercase tracking-widest">
      Crawlers Inc. | Don't die.
    </footer>

    <div v-if="selectedSkill" class="absolute inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200" @click.self="selectedSkill = null">
      
      <div class="bg-gray-900 border-2 border-green-500 w-full max-w-sm p-1 shadow-[0_0_50px_rgba(34,197,94,0.2)] transform scale-100 animate-in zoom-in-95 duration-200">
        
        <div class="border border-green-900/50 p-5 flex flex-col gap-4 relative overflow-hidden">
          
          <div class="absolute inset-0 bg-green-500/5 pointer-events-none" style="background-image: linear-gradient(transparent 50%, rgba(34,197,94,0.05) 50%); background-size: 100% 4px;"></div>

          <div class="flex justify-between items-start z-10">
            <div>
              <div class="text-[10px] text-green-600 uppercase tracking-widest mb-1">Skill Analysis</div>
              <h2 class="text-2xl font-bold text-white uppercase tracking-tight">{{ selectedSkill.name }}</h2>
            </div>
            <div class="bg-green-900/30 border border-green-500/50 px-3 py-1 text-green-400 font-mono text-xl font-bold rounded">
              LVL {{ selectedSkill.level }}
            </div>
          </div>

          <div class="h-px w-full bg-gradient-to-r from-transparent via-green-500 to-transparent opacity-50"></div>

          <p class="text-green-300/90 font-mono text-sm leading-relaxed z-10 min-h-[3rem]">
            {{ selectedSkill.desc }}
          </p>

          <div class="mt-4 z-10">
            
            <div v-if="!isRolling && !rollResult" class="flex justify-between items-center">
              <button @click="selectedSkill = null" class="text-gray-500 hover:text-white text-xs uppercase tracking-widest">Cancel</button>
              
              <button 
                @click="performRoll"
                class="bg-green-600 hover:bg-green-500 text-black font-bold py-3 px-8 text-lg uppercase tracking-widest clip-path-polygon hover:shadow-[0_0_20px_rgba(34,197,94,0.8)] transition-all animate-pulse"
                style="clip-path: polygon(10% 0, 100% 0, 100% 70%, 90% 100%, 0 100%, 0 30%);"
              >
                ROLL d20 + {{ selectedSkill?.level }}
              </button>
            </div>

            <div v-if="isRolling" class="text-center py-4">
              <div class="inline-block w-8 h-8 border-4 border-green-500 border-t-transparent rounded-full animate-spin"></div>
              <div class="text-green-500 text-xs mt-2 uppercase tracking-widest animate-pulse">Calculating Trajectory...</div>
            </div>

            <div v-if="rollResult" class="text-center animate-in zoom-in duration-300">
               <div class="text-[10px] text-gray-400 uppercase tracking-widest mb-1">Result</div>
               
               <div class="flex items-center justify-center gap-2 text-4xl font-black text-white drop-shadow-[0_0_10px_rgba(255,255,255,0.8)]">
                 <span :class="{'text-red-500': rollResult.d20 === 1, 'text-yellow-400': rollResult.d20 === 20}">
                   {{ rollResult.d20 }}
                 </span>
                 <span class="text-lg text-gray-500 font-normal">+ {{ rollResult.mod }}</span>
                 <span class="text-gray-600">=</span>
                 <span class="text-green-400 text-5xl">{{ rollResult.total }}</span>
               </div>

               <div v-if="rollResult.d20 === 20" class="text-yellow-400 font-bold uppercase tracking-widest mt-2 text-sm animate-bounce">CRITICAL SUCCESS</div>
               <div v-if="rollResult.d20 === 1" class="text-red-500 font-bold uppercase tracking-widest mt-2 text-sm animate-bounce">CRITICAL FAILURE</div>
            </div>

          </div>

        </div>
      </div>
    </div>

  </div>
</template>