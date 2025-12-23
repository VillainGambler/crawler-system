from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

# --- SUB-MODELS ---

class Stats(BaseModel):
    strength: int = Field(default=10, ge=0)
    dexterity: int = Field(default=10, ge=0)
    constitution: int = Field(default=10, ge=0)
    intelligence: int = Field(default=10, ge=0)
    charisma: int = Field(default=10, ge=0)

class Vitals(BaseModel):
    current: int = 10
    max: int = 10
    temp: int = 0

class Item(BaseModel):
    name: str
    type: str = "General"
    count: int = 1
    description: Optional[str] = None
    # Added stats to match Frontend/Game logic
    stats: Optional[Dict[str, Any]] = None

class EquipmentSlot(BaseModel):
    name: str
    type: str
    stats: Optional[Dict[str, int]] = None

class Equipment(BaseModel):
    right_hand: Optional[EquipmentSlot] = None
    left_hand: Optional[EquipmentSlot] = None
    head: Optional[EquipmentSlot] = None
    body: Optional[EquipmentSlot] = None
    feet: Optional[EquipmentSlot] = None

# --- MAIN MODEL ---

class Character(BaseModel):
    id: str
    name: str
    race: str = "Unknown"
    player_class: str = "Crawler"
    level: int = 1
    gold: int = 0
    
    stats: Stats
    hp: Vitals
    mp: Optional[Vitals] = None
    sp: Optional[Vitals] = None
    
    skills: Dict[str, int] = {}
    feats: List[str] = []
    inventory: List[Item] = []
    equipment: Equipment = {}