from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

# --- SUB-MODELS (The ingredients) ---

class Stats(BaseModel):
    strength: int = Field(ge=0)
    dexterity: int = Field(ge=0)
    constitution: int = Field(ge=0)
    intelligence: int = Field(ge=0)
    charisma: int = Field(ge=0)

class Vitals(BaseModel):
    current: int
    max: int

class Item(BaseModel):
    name: str
    type: str = "General"
    count: int = 1
    description: Optional[str] = None

class EquipmentSlot(BaseModel):
    name: str
    type: str
    stats: Optional[Dict[str, int]] = None

class Equipment(BaseModel):
    # Optional because you might be naked
    right_hand: Optional[EquipmentSlot] = None
    left_hand: Optional[EquipmentSlot] = None
    head: Optional[EquipmentSlot] = None
    body: Optional[EquipmentSlot] = None
    feet: Optional[EquipmentSlot] = None

# --- MAIN MODEL (The Character Sheet) ---

class Character(BaseModel):
    id: str
    name: str
    race: str = "Unknown"
    player_class: str = "Peasant"
    level: int = 1
    
    # Nested Models
    stats: Stats
    hp: Vitals
    mp: Vitals
    sp: Vitals
    
    # The Missing Pieces!
    skills: Dict[str, int] = {}     # e.g. {"explosives": 10}
    feats: List[str] = []           # e.g. ["Toughness"]
    inventory: List[Item] = []      # The Backpack
    equipment: Equipment = {}       # The Armor/Weapons
    hotbar: List[Optional[Any]] = [None] * 6 # 6 Quick Slots