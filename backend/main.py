from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from models import Character  
import database
from pydantic import BaseModel
from fastapi import WebSocket, WebSocketDisconnect
from connection_manager import ConnectionManager


# Initialize the Manager
manager = ConnectionManager()

app = FastAPI(title="The Crawler System", version="0.2.0")

# --- CORS CONFIGURATION (Crucial for iPad) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all connections (Safe for local dev)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- READ (GET) with DEBUG LOGGING ---
@app.get("/character/{character_id}", response_model=Character)
async def read_character(character_id: str):
    try:
        print(f"DEBUG: Attempting to fetch {character_id}...")
        
        # 1. Fetch raw data from DynamoDB
        data = database.get_character(character_id)
        print(f"DEBUG: Database returned: {data}")
        
        if not data:
            print("DEBUG: Character not found in DB.")
            raise HTTPException(status_code=404, detail="Character not found")
        
        # 2. Validate data manually to catch structure errors
        print("DEBUG: Validating data against Pydantic model...")
        validated_char = Character(**data)
        print("DEBUG: Validation successful!")
        
        return validated_char

    except Exception as e:
        # This prints the REAL error to your terminal
        print(f"CRITICAL ERROR: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# --- CREATE (POST) ---
@app.post("/character/", response_model=Character)
async def create_new_character(character: Character):
    """
    Save a new character to the Cloud.
    """
    # Convert Pydantic model to a standard Dictionary
    character_dict = character.model_dump()
    
    # Send to AWS
    database.create_character(character_dict)
    
    return character

# --- NEW DATA MODEL (For the request body) ---
class DamageRequest(BaseModel):
    amount: int  # e.g., -5 for damage, +5 for healing

@app.post("/character/{character_id}/adjust-hp")
async def adjust_hp(character_id: str, action: DamageRequest):
    # 1. Update DB & Get Full Character
    full_char = database.update_hp(character_id, action.amount)
    if not full_char:
        raise HTTPException(status_code=500, detail="Failed to update HP")

    # 2. Prepare Data
    hp_block = full_char.get("hp", {})
    clean_hp = {k: int(v) for k, v in hp_block.items()}
    char_name = full_char.get("name", "Unknown Crawler") # Get name for the log

    # 3. Broadcast 1: The Number Change
    await manager.broadcast(character_id, {"type": "HP_UPDATE", "new_hp": clean_hp})

    # 4. Broadcast 2: The Combat Log
    # Determine flavor text
    if action.amount > 0:
        log_msg = f"{char_name} healed for {action.amount} HP."
    else:
        log_msg = f"{char_name} took {abs(action.amount)} damage!"

    await manager.broadcast(character_id, {"type": "LOG", "message": log_msg})
    
    return {"status": "success", "new_hp": clean_hp}
# --- NEW MODEL ---
class ItemRequest(BaseModel):
    item_name: str

# --- NEW ENDPOINT ---
@app.post("/character/{character_id}/use-item")
async def use_item(character_id: str, request: ItemRequest):
    """
    Finds an item, decreases count by 1 (or removes it), saves, and narrates the action.
    """
    print(f"DEBUG: {character_id} is trying to use {request.item_name}...")

    # 1. Fetch current state
    data = database.get_character(character_id)
    if not data:
        raise HTTPException(status_code=404, detail="Character not found")
    
    character = Character(**data)

    # 2. Find and Modify the Item
    found = False
    for i, item in enumerate(character.inventory):
        if item.name == request.item_name:
            found = True
            if item.count > 1:
                item.count -= 1
                print(f"DEBUG: Decremented {item.name} to {item.count}")
            else:
                # Remove it entirely if count was 1
                character.inventory.pop(i)
                print(f"DEBUG: Consumed last {item.name}")
            break
    
    if not found:
        raise HTTPException(status_code=404, detail="Item not found in inventory")

    # 3. Save to Database
    # We convert the Pydantic model back to a dictionary for DynamoDB
    updated_data = character.model_dump()
    success = database.create_character(updated_data)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to save inventory")

    # 4. Broadcast Updates
    # A) Tell frontend to reload data (syncs the inventory count)
    await manager.broadcast(character_id, {"type": "FULL_REFRESH"})
    
    # B) Tell frontend to add a log entry
    await manager.broadcast(character_id, {
        "type": "LOG", 
        "message": f"{character.name} used {request.item_name}."
    })

    return character

@app.websocket("/ws/{character_id}")
async def websocket_endpoint(websocket: WebSocket, character_id: str):
    await manager.connect(websocket, character_id)
    try:
        while True:
            # We just listen. We don't expect the client to say much, 
            # but we need this loop to keep the connection alive.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, character_id)
# --- STATIC FILES (THE FRONTEND) ---

# Get the absolute path to the frontend/dist folder
# We assume backend/main.py is one level deeper than the project root
# So we go up one level (..), then into frontend/dist
frontend_path = os.path.join(os.path.dirname(__file__), "../frontend/dist")

# 1. Mount the 'assets' folder (CSS/JS)
app.mount("/assets", StaticFiles(directory=os.path.join(frontend_path, "assets")), name="assets")

@app.get("/")
async def serve_root():
    return FileResponse(os.path.join(frontend_path, "index.html"))

# 2. Catch-All Route for SPA (Single Page Application)
# If the user goes to /character/carl, Vue handles it, not Python.
# So Python just needs to return index.html and let Vue take over.
@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    # If API is requested, but not found, return 404 (don't serve HTML)
    if full_path.startswith("api") or full_path.startswith("ws"):
        raise HTTPException(status_code=404)
    
    # Otherwise, return the app
    return FileResponse(os.path.join(frontend_path, "index.html"))