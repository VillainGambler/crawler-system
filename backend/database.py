import boto3
import os
from decimal import Decimal
from typing import Optional, List, Dict, Any
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()

REGION = os.getenv("AWS_REGION", "us-east-1")
TABLE_NAME = os.getenv("DYNAMODB_TABLE", "crawler-system-data")

dynamodb = boto3.resource("dynamodb", region_name=REGION)
table = dynamodb.Table(TABLE_NAME)

# --- HELPERS ---
def convert_decimal(obj):
    if isinstance(obj, list):
        return [convert_decimal(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: convert_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, Decimal):
        return int(obj)
    return obj

# --- CRUD OPERATIONS ---

def get_character(char_id: str) -> Optional[Dict[str, Any]]:
    try:
        response = table.get_item(Key={'pk': 'CRAWL#101', 'sk': f"PLAYER#{char_id}"})
        if 'Item' not in response:
            return None
        
        item = convert_decimal(response['Item'])
        
        # Ensure defaults for frontend safety
        return {
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
    except ClientError as e:
        print(f"DB Error: {e}")
        return None

def update_inventory(char_id: str, inventory: List[Dict]):
    table.update_item(
        Key={'pk': 'CRAWL#101', 'sk': f"PLAYER#{char_id}"},
        UpdateExpression="SET inventory = :inv",
        ExpressionAttributeValues={':inv': inventory}
    )

def update_gold(char_id: str, amount: int):
    # Atomic update
    response = table.update_item(
        Key={'pk': 'CRAWL#101', 'sk': f"PLAYER#{char_id}"},
        UpdateExpression="SET gold = if_not_exists(gold, :zero) + :val",
        ExpressionAttributeValues={':val': amount, ':zero': 0},
        ReturnValues="UPDATED_NEW"
    )
    return convert_decimal(response.get('Attributes', {}))

def update_hp(char_id: str, amount: int):
    # Atomic update for nested map
    table.update_item(
        Key={'pk': 'CRAWL#101', 'sk': f"PLAYER#{char_id}"},
        UpdateExpression="SET #h.#c = #h.#c + :val",
        ExpressionAttributeNames={'#h': 'hp', '#c': 'current'},
        ExpressionAttributeValues={':val': amount}
    )

def level_up_character(char_id: str):
    table.update_item(
        Key={'pk': 'CRAWL#101', 'sk': f"PLAYER#{char_id}"},
        UpdateExpression="SET #l = #l + :val",
        ExpressionAttributeNames={'#l': 'level'},
        ExpressionAttributeValues={':val': 1}
    )