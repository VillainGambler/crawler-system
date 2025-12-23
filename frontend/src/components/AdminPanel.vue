<script setup lang="ts">
import { ref } from 'vue'

const selectedChar = ref('carl_001')
const gmPassword = ref('') // Store the password locally
const characters = [
  { id: 'carl_001', name: 'Carl' },
  { id: 'donut_001', name: 'Princess Donut' }
]

// Loot Form State
const newItem = ref({
  name: '',
  type: 'Consumable',
  count: 1
})

const isSending = ref(false)
const statusMsg = ref('')

// Helper for Auth Headers
const getHeaders = () => {
  return {
    'Content-Type': 'application/json',
    'X-GM-Key': gmPassword.value // Inject Security Token
  }
}

// --- FUNCTION 1: GIVE LOOT ---
async function sendLoot() {
  if (!newItem.value.name) return
  isSending.value = true
  statusMsg.value = "Transmitting..."

  try {
    const res = await fetch(`/character/${selectedChar.value}/add-item`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify(newItem.value)
    })
    
    if (!res.ok) throw new Error(await res.text())

    statusMsg.value = `SUCCESS: Sent ${newItem.value.count}x ${newItem.value.name} to ${selectedChar.value}`
    newItem.value.name = ''
    newItem.value.count = 1
  } catch (err: any) {
    statusMsg.value = "ERROR: Transmission Failed (Check Password?)"
    console.error(err)
  } finally {
    isSending.value = false
    setTimeout(() => statusMsg.value = '', 3000)
  }
}

// --- FUNCTION 2: ADJUST HP ---
async function adjustRemoteHP(amount: number) {
  try {
    const res = await fetch(`/character/${selectedChar.value}/adjust-hp?amount=${amount}`, { 
      method: 'POST',
      headers: getHeaders()
    })
    if (!res.ok) throw new Error(await res.text())
    
    statusMsg.value = `Updated HP for ${selectedChar.value}`
    setTimeout(() => statusMsg.value = '', 2000)
  } catch (e) {
    console.error(e)
    statusMsg.value = "ERROR: Access Denied"
  }
}

// --- FUNCTION 3: LEVEL UP ---
async function triggerLevelUp() {
  if(!confirm("Are you sure you want to LEVEL UP this character?")) return;
  
  try {
    const res = await fetch(`/character/${selectedChar.value}/level-up`, { 
      method: 'POST',
      headers: getHeaders()
    })
    if (!res.ok) throw new Error(await res.text())

    statusMsg.value = `LEVEL UP: ${selectedChar.value}`
    setTimeout(() => statusMsg.value = '', 2000)
  } catch (e) {
    console.error(e)
    statusMsg.value = "ERROR: Level Up Failed"
  }
}

// --- FUNCTION 4: ADJUST GOLD ---
async function adjustGold(amount: number) {
  try {
    const res = await fetch(`/character/${selectedChar.value}/adjust-gold?amount=${amount}`, { 
      method: 'POST',
      headers: getHeaders()
    })
    if (!res.ok) throw new Error(await res.text())

    statusMsg.value = `Transaction Complete: ${amount} GP`
    setTimeout(() => statusMsg.value = '', 2000)
  } catch (e) {
    console.error(e)
    statusMsg.value = "ERROR: Transaction Failed"
  }
}
</script>

<template>
  <div class="min-h-screen bg-black text-red-500 font-mono p-8 flex flex-col items-center">
    
    <h1 class="text-4xl font-bold uppercase tracking-widest border-b-2 border-red-600 pb-2 mb-8 drop-shadow-[0_0_10px_rgba(220,38,38,0.7)]">
      SYSTEM OVERRIDE // ADMIN
    </h1>

    <div class="w-full max-w-md space-y-6">
      
      <div class="bg-gray-900/50 p-4 border border-red-800 rounded">
        <label class="block text-xs uppercase tracking-widest text-red-700 mb-2">Security Clearance Code</label>
        <input 
          v-model="gmPassword" 
          type="password" 
          placeholder="ENTER GM TOKEN..." 
          class="w-full bg-black border border-red-900 p-2 text-white focus:border-red-500 focus:outline-none placeholder-red-900/50"
        >
      </div>

      <div class="bg-gray-900/50 p-4 border border-red-800 rounded">
        <label class="block text-xs uppercase tracking-widest text-red-700 mb-2">Target Entity</label>
        <div class="flex gap-2">
          <button 
            v-for="char in characters" 
            :key="char.id"
            @click="selectedChar = char.id"
            class="flex-1 py-3 border border-red-900 hover:bg-red-900/20 transition-all uppercase font-bold"
            :class="selectedChar === char.id ? 'bg-red-900/40 border-red-500 text-white' : 'text-gray-500'"
          >
            {{ char.name }}
          </button>
        </div>
      </div>

      <div class="bg-gray-900/50 p-4 border border-red-800 rounded relative">
        <div class="absolute top-0 right-0 bg-red-900 text-white text-[10px] px-2 py-0.5 uppercase">Bio-Metrics</div>
        
        <div class="grid grid-cols-2 gap-4 mt-2">
          <div class="space-y-1">
            <label class="text-xs text-red-700 block">Inflict Pain</label>
            <div class="flex gap-1">
              <button @click="adjustRemoteHP(-1)" class="flex-1 bg-red-900 hover:bg-red-700 text-white font-bold py-2 rounded">-1</button>
              <button @click="adjustRemoteHP(-5)" class="flex-1 bg-red-900 hover:bg-red-700 text-white font-bold py-2 rounded">-5</button>
            </div>
          </div>
          <div class="space-y-1">
             <label class="text-xs text-green-700 block">Restoration</label>
             <div class="flex gap-1">
               <button @click="adjustRemoteHP(1)" class="flex-1 bg-green-900 hover:bg-green-700 text-white font-bold py-2 rounded">+1</button>
               <button @click="adjustRemoteHP(5)" class="flex-1 bg-green-900 hover:bg-green-700 text-white font-bold py-2 rounded">+5</button>
             </div>
          </div>
        </div>

        <button @click="triggerLevelUp" class="w-full mt-4 border border-yellow-600 text-yellow-500 py-2 uppercase text-xs tracking-widest hover:bg-yellow-900/20 transition-all">
          ⚠️ Grant Level Up ⚠️
        </button>
      </div>
      <div class="bg-gray-900/50 p-4 border border-red-800 rounded relative">
        <div class="absolute top-0 right-0 bg-red-900 text-white text-[10px] px-2 py-0.5 uppercase">Economy</div>
        
        <div class="grid grid-cols-2 gap-4 mt-2">
           <div class="space-y-1">
             <label class="text-xs text-red-700 block">Tax / Fine</label>
             <div class="flex gap-1">
               <button @click="adjustGold(-10)" class="flex-1 bg-red-900 hover:bg-red-700 text-white font-bold py-2 rounded">-10</button>
               <button @click="adjustGold(-100)" class="flex-1 bg-red-900 hover:bg-red-700 text-white font-bold py-2 rounded">-100</button>
             </div>
           </div>
           <div class="space-y-1">
              <label class="text-xs text-yellow-700 block">Reward</label>
              <div class="flex gap-1">
                <button @click="adjustGold(10)" class="flex-1 bg-yellow-900/50 hover:bg-yellow-600 text-white font-bold py-2 rounded border border-yellow-700">+10</button>
                <button @click="adjustGold(100)" class="flex-1 bg-yellow-900/50 hover:bg-yellow-600 text-white font-bold py-2 rounded border border-yellow-700">+100</button>
              </div>
           </div>
        </div>
      </div>
      <div class="bg-gray-900/50 p-4 border border-red-800 rounded relative">
        <div class="absolute top-0 right-0 bg-red-900 text-white text-[10px] px-2 py-0.5 uppercase">Loot Box Protocol</div>
        
        <div class="space-y-4 mt-2">
          <div>
            <label class="block text-xs text-red-700 mb-1">Item Name</label>
            <input v-model="newItem.name" type="text" placeholder="e.g. Healing Potion" 
                   class="w-full bg-black border border-red-900 p-2 text-white focus:border-red-500 focus:outline-none placeholder-gray-700">
          </div>
          
          <div class="flex gap-4">
            <div class="flex-1">
              <label class="block text-xs text-red-700 mb-1">Type</label>
              <select v-model="newItem.type" class="w-full bg-black border border-red-900 p-2 text-white focus:border-red-500 focus:outline-none">
                <option>Consumable</option>
                <option>Weapon</option>
                <option>Armor</option>
                <option>Trophy</option>
                <option>Quest Item</option>
              </select>
            </div>
            <div class="w-20">
              <label class="block text-xs text-red-700 mb-1">Qty</label>
              <input v-model="newItem.count" type="number" min="1" 
                     class="w-full bg-black border border-red-900 p-2 text-white focus:border-red-500 focus:outline-none">
            </div>
          </div>

          <button 
            @click="sendLoot"
            :disabled="isSending || !newItem.name"
            class="w-full py-3 bg-red-900/20 border border-red-600 text-red-500 font-bold uppercase tracking-widest hover:bg-red-600 hover:text-white transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {{ isSending ? 'Transmitting...' : 'GRANT ITEM' }}
          </button>
        </div>
      </div>
      
      <div v-if="statusMsg" class="text-center text-xs text-white animate-pulse mt-4">
            {{ statusMsg }}
      </div>

    </div>
  </div>
</template>