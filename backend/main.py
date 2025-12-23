from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import boto3
import os
import json
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from decimal import Decimal
from pydantic import BaseModel
from typing import Optional, Dict, Any
import random

app = FastAPI()

# --- DATA MODELS ---
class ItemModel(BaseModel):
    name: str
    type: str
    count: int = 1
    stats: Optional[Dict[str, Any]] = None

# --- DYNAMODB CONNECTION ---
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('crawler-system-data')

# --- WEBSOCKET MANAGER ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, char_id: str, websocket: WebSocket):
        await websocket.accept()
        if char_id not in self.active_connections:
            self.active_connections[char_id] = []
        self.active_connections[char_id].append(websocket)

    def disconnect(self, char_id: str, websocket: WebSocket):
        if char_id in self.active_connections:
            self.active_connections[char_id].remove(websocket)
            if not self.active_connections[char_id]:
                del self.active_connections[char_id]

    async def broadcast(self, char_id: str, message: dict):
        if char_id in self.active_connections:
            json_msg = json.dumps(message, default=str)
            for connection in self.active_connections[char_id]:
                await connection.send_text(json_msg)

manager = ConnectionManager()

# --- HELPER: Decimal Encoder ---
# DynamoDB returns numbers as Decimals. We need to convert them to int for JSON.
def convert_decimal(obj):
    if isinstance(obj, list):
        return [convert_decimal(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: convert_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, Decimal):
        return int(obj)
    return obj

# --- HELPER: Get Character ---
def get_character_from_db(char_id: str):
    try:
        # UPDATED KEY STRUCTURE: CRAWL#101 / PLAYER#{id}
        response = table.get_item(Key={'pk': 'CRAWL#101', 'sk': f"PLAYER#{char_id}"})
        if 'Item' not in response:
            return None
        
        item = convert_decimal(response['Item'])
        
        # Structure the data for the Frontend
        # We fetch nested objects (hp, stats) directly since your DB has them nested
        character_data = {
            "name": item.get('name', 'Unknown'),
            "race": item.get('race', 'Unknown'),
            "player_class": item.get('player_class', 'Crawler'),
            "level": item.get('level', 1),
            "gold": int(item.get('gold', 0)),
            "hp": {
                "current": item.get('hp', {}).get('current', 10),
                "max": item.get('hp', {}).get('max', 10),
                "temp": 0
            },
            "stats": item.get('stats', {
                "strength": 10, "dexterity": 10, "constitution": 10,
                "intelligence": 10, "charisma": 10
            }),
            "skills": item.get('skills', {}),
            "feats": item.get('feats', []),
            "inventory": item.get('inventory', []),
            "equipment": item.get('equipment', {})
        }
        return character_data
    except ClientError as e:
        print(f"DB Error: {e}")
        return None

# --- API ENDPOINTS ---

class RollRequest(BaseModel):
    skill_name: str

@app.post("/character/{char_id}/roll")
async def roll_skill(char_id: str, request: RollRequest):
    """
    Rolls a d20 + Skill Modifier.
    """
    char_data = get_character_from_db(char_id)
    if not char_data:
        raise HTTPException(status_code=404)

    skill_name = request.skill_name.lower()
    # Default to 0 if skill not found
    modifier = char_data['skills'].get(skill_name, 0)
    
    # THE ROLL
    d20 = random.randint(1, 20)
    total = d20 + modifier
    
    # Crit Logic
    crit_msg = ""
    if d20 == 20:
        crit_msg = " [CRITICAL SUCCESS!]"
    elif d20 == 1:
        crit_msg = " [CRITICAL FAILURE!]"

    # Broadcast Log
    log_msg = f"Rolled {request.skill_name.title()}: {d20} + {modifier} = {total}{crit_msg}"
    
    await manager.broadcast(char_id, {"type": "log", "message": log_msg})
    
    # We also send a special "roll_result" event so the frontend can show a popup
    await manager.broadcast(char_id, {
        "type": "roll_result", 
        "payload": {
            "skill": request.skill_name,
            "d20": d20,
            "mod": modifier,
            "total": total,
            "crit": d20 == 20 or d20 == 1
        }
    })
    
    return {"status": "success", "total": total}

@app.post("/character/{char_id}/add-item")
async def add_item(char_id: str, item: ItemModel):
    """
    God Mode: Grant an item to a player.
    """
    char_data = get_character_from_db(char_id)
    if not char_data:
        raise HTTPException(status_code=404)
        
    inventory = char_data['inventory']
    
    # Check if item already exists (stack it)
    found = False
    for inv_item in inventory:
        if inv_item['name'] == item.name and inv_item.get('type') == item.type:
            current_count = inv_item.get('count', 1)
            inv_item['count'] = current_count + item.count
            found = True
            break
            
    # If not found, append new item
    if not found:
        new_item = item.dict()
        inventory.append(new_item)
        
    # Save to DB
    table.update_item(
        Key={'pk': 'CRAWL#101', 'sk': f"PLAYER#{char_id}"},
        UpdateExpression="SET inventory = :inv",
        ExpressionAttributeValues={':inv': inventory}
    )

@app.post("/character/{char_id}/level-up")
async def level_up(char_id: str):
    """
    Increases Level by 1 and heals to max.
    """
    try:
        # Atomic update: Level + 1
        table.update_item(
            Key={'pk': 'CRAWL#101', 'sk': f"PLAYER#{char_id}"},
            UpdateExpression="SET #l = #l + :val",
            ExpressionAttributeNames={'#l': 'level'},
            ExpressionAttributeValues={':val': 1}
        )
        
        # Get new state
        updated_char = get_character_from_db(char_id)
        
        # Broadcast
        await manager.broadcast(char_id, {"type": "update", "payload": updated_char})
        await manager.broadcast(char_id, {"type": "log", "message": f"LEVEL UP! You are now Level {updated_char['level']}!"})
        
        return {"status": "success", "new_level": updated_char['level']}
    except ClientError as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    # Broadcast Update
    updated_char = get_character_from_db(char_id)
    await manager.broadcast(char_id, {"type": "update", "payload": updated_char})
    await manager.broadcast(char_id, {"type": "log", "message": f"SYSTEM GRANTED: {item.name} (x{item.count})"})
    
    return {"status": "success", "inventory": inventory}

@app.get("/character/{char_id}")
async def get_character(char_id: str):
    data = get_character_from_db(char_id)
    if not data:
        raise HTTPException(status_code=404, detail="Character not found")
    return data

@app.post("/character/{char_id}/adjust-gold")
async def adjust_gold(char_id: str, amount: int):
    """
    Adjusts Gold by 'amount' (Positive to give, Negative to take).
    """
    try:
        # 1. Update DynamoDB (Atomic Update)
        # If 'gold' doesn't exist yet, this might fail without an if_not_exists, 
        # so we use a robust expression: SET gold = if_not_exists(gold, :zero) + :val
        table.update_item(
            Key={'pk': 'CRAWL#101', 'sk': f"PLAYER#{char_id}"},
            UpdateExpression="SET gold = if_not_exists(gold, :zero) + :val",
            ExpressionAttributeValues={':val': amount, ':zero': 0},
            ReturnValues="UPDATED_NEW"
        )
        
        # 2. Broadcast
        updated_char = get_character_from_db(char_id)
        await manager.broadcast(char_id, {"type": "update", "payload": updated_char})
        
        # 3. Log
        action = "Received" if amount > 0 else "Paid"
        log_msg = f"FINANCE: {action} {abs(amount)} Gold."
        await manager.broadcast(char_id, {"type": "log", "message": log_msg})
        
        return {"status": "success", "new_gold": updated_char['gold']}
        
    except ClientError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/character/{char_id}/adjust-hp")
async def adjust_hp(char_id: str, amount: int):
    try:
        # UPDATED: We need to update the NESTED map 'hp.current'
        # We use ExpressionAttributeNames to safely target "hp" and "current"
        response = table.update_item(
            Key={'pk': 'CRAWL#101', 'sk': f"PLAYER#{char_id}"},
            UpdateExpression="SET #h.#c = #h.#c + :val",
            ExpressionAttributeNames={'#h': 'hp', '#c': 'current'},
            ExpressionAttributeValues={':val': amount},
            ReturnValues="UPDATED_NEW"
        )
        
        # Broadcast
        updated_char = get_character_from_db(char_id)
        await manager.broadcast(char_id, {"type": "update", "payload": updated_char})
        
        # Log
        action = "Healed" if amount > 0 else "Took Damage"
        log_msg = f"{action} ({abs(amount)}). HP is now {updated_char['hp']['current']}."
        await manager.broadcast(char_id, {"type": "log", "message": log_msg})
        
        return {"status": "success"}
        
    except ClientError as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/character/{char_id}/use-item")
async def use_item(char_id: str, item_index: int):
    # Fetch -> Modify -> Save pattern is safest for list manipulation
    char_data = get_character_from_db(char_id)
    if not char_data:
        raise HTTPException(status_code=404)
        
    inventory = char_data['inventory']
    
    if item_index < 0 or item_index >= len(inventory):
        raise HTTPException(status_code=400, detail="Invalid item index")
        
    item = inventory[item_index]
    item_name = item['name']
    
    # Logic: If count > 1, decrease count. Else remove.
    # Note: DB might store count as int or might allow missing count (implies 1)
    current_count = item.get('count', 1)
    
    if current_count > 1:
        inventory[item_index]['count'] = current_count - 1
    else:
        inventory.pop(item_index)
        
    # Save back to DB
    table.update_item(
        Key={'pk': 'CRAWL#101', 'sk': f"PLAYER#{char_id}"},
        UpdateExpression="SET inventory = :inv",
        ExpressionAttributeValues={':inv': inventory}
    )
    
    updated_char = get_character_from_db(char_id)
    await manager.broadcast(char_id, {"type": "update", "payload": updated_char})
    await manager.broadcast(char_id, {"type": "log", "message": f"Used {item_name}."})
    
    return {"status": "success", "inventory": inventory}

@app.websocket("/ws/{char_id}")
async def websocket_endpoint(websocket: WebSocket, char_id: str):
    await manager.connect(char_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(char_id, websocket)

# --- DEPLOYMENT ---
frontend_path = os.path.join(os.path.dirname(__file__), "../frontend/dist")
if os.path.exists(frontend_path):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_path, "assets")), name="assets")
    @app.get("/")
    async def serve_root():
        return FileResponse(os.path.join(frontend_path, "index.html"))
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api") or full_path.startswith("ws"):
            raise HTTPException(status_code=404)
        return FileResponse(os.path.join(frontend_path, "index.html"))