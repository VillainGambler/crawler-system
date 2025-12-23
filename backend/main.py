from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
import random
import json

# --- MODULE IMPORTS ---
from connection_manager import ConnectionManager
from models import Item
import database as db

app = FastAPI()
manager = ConnectionManager()

# --- API ENDPOINTS ---

class RollRequest(BaseModel):
    skill_name: str

@app.get("/character/{char_id}")
async def get_character(char_id: str):
    data = db.get_character(char_id)
    if not data:
        raise HTTPException(status_code=404, detail="Character not found")
    return data

@app.post("/character/{char_id}/roll")
async def roll_skill(char_id: str, request: RollRequest):
    char_data = db.get_character(char_id)
    if not char_data:
        raise HTTPException(status_code=404)

    skill_name = request.skill_name.lower()
    modifier = char_data['skills'].get(skill_name, 0)
    
    # THE ROLL
    d20 = random.randint(1, 20)
    total = d20 + modifier
    
    crit_msg = ""
    if d20 == 20: crit_msg = " [CRITICAL SUCCESS!]"
    elif d20 == 1: crit_msg = " [CRITICAL FAILURE!]"

    log_msg = f"Rolled {request.skill_name.title()}: {d20} + {modifier} = {total}{crit_msg}"
    
    await manager.broadcast(char_id, {"type": "log", "message": log_msg})
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
async def add_item(char_id: str, item: Item):
    char_data = db.get_character(char_id)
    if not char_data:
        raise HTTPException(status_code=404)
        
    inventory = char_data['inventory']
    
    # Stack Logic
    found = False
    for inv_item in inventory:
        if inv_item['name'] == item.name and inv_item.get('type') == item.type:
            inv_item['count'] = inv_item.get('count', 1) + item.count
            found = True
            break
            
    if not found:
        # Pydantic .dict() or .model_dump() (v2)
        new_item = item.dict() if hasattr(item, 'dict') else item.model_dump()
        inventory.append(new_item)
        
    db.update_inventory(char_id, inventory)
    
    # Broadcast
    updated_char = db.get_character(char_id)
    await manager.broadcast(char_id, {"type": "update", "payload": updated_char})
    await manager.broadcast(char_id, {"type": "log", "message": f"SYSTEM GRANTED: {item.name} (x{item.count})"})
    
    return {"status": "success"}

@app.post("/character/{char_id}/use-item")
async def use_item(char_id: str, item_index: int):
    char_data = db.get_character(char_id)
    if not char_data:
        raise HTTPException(status_code=404)
        
    inventory = char_data['inventory']
    if item_index < 0 or item_index >= len(inventory):
        raise HTTPException(status_code=400, detail="Invalid item index")
        
    item = inventory[item_index]
    item_name = item['name']
    
    current_count = item.get('count', 1)
    if current_count > 1:
        inventory[item_index]['count'] = current_count - 1
    else:
        inventory.pop(item_index)
        
    db.update_inventory(char_id, inventory)
    
    updated_char = db.get_character(char_id)
    await manager.broadcast(char_id, {"type": "update", "payload": updated_char})
    await manager.broadcast(char_id, {"type": "log", "message": f"Used {item_name}."})
    
    return {"status": "success"}

@app.post("/character/{char_id}/adjust-hp")
async def adjust_hp(char_id: str, amount: int):
    try:
        db.update_hp(char_id, amount)
        
        updated_char = db.get_character(char_id)
        await manager.broadcast(char_id, {"type": "update", "payload": updated_char})
        
        action = "Healed" if amount > 0 else "Took Damage"
        log_msg = f"{action} ({abs(amount)}). HP is now {updated_char['hp']['current']}."
        await manager.broadcast(char_id, {"type": "log", "message": log_msg})
        
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/character/{char_id}/adjust-gold")
async def adjust_gold(char_id: str, amount: int):
    try:
        db.update_gold(char_id, amount)
        updated_char = db.get_character(char_id)
        
        await manager.broadcast(char_id, {"type": "update", "payload": updated_char})
        
        action = "Received" if amount > 0 else "Paid"
        log_msg = f"FINANCE: {action} {abs(amount)} Gold."
        await manager.broadcast(char_id, {"type": "log", "message": log_msg})
        
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/character/{char_id}/level-up")
async def level_up(char_id: str):
    try:
        db.level_up_character(char_id)
        updated_char = db.get_character(char_id)
        
        await manager.broadcast(char_id, {"type": "update", "payload": updated_char})
        await manager.broadcast(char_id, {"type": "log", "message": f"LEVEL UP! You are now Level {updated_char['level']}!"})
        
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws/{char_id}")
async def websocket_endpoint(websocket: WebSocket, char_id: str):
    await manager.connect(websocket, char_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, char_id)

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