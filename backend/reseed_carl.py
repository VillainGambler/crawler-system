import boto3
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

REGION = os.getenv("AWS_REGION", "us-east-1")
TABLE_NAME = os.getenv("DYNAMODB_TABLE", "crawler-system-data")

# Connect to DynamoDB
dynamodb = boto3.resource("dynamodb", region_name=REGION)
table = dynamodb.Table(TABLE_NAME)

# THE PERFECT CARL DATA
clean_carl = {
    "pk": "CRAWL#101",
    "sk": "PLAYER#carl_001",
    "id": "carl_001",
    "name": "Carl",
    "race": "Human",
    "player_class": "Dungeon Crawler",
    "level": 5,
    "stats": {
        "strength": 18,
        "dexterity": 14,
        "constitution": 16,
        "intelligence": 10,
        "charisma": 12
    },
    "hp": {"current": 40, "max": 40},
    "mp": {"current": 0, "max": 0},
    "sp": {"current": 100, "max": 100},
    "skills": {"brawling": 5},
    "feats": [],
    "equipment": {
        "right_hand": None,
        "body": None
    },
    "inventory": [],
    "hotbar": [None] * 6
}

print(f"Injecting clean data into {TABLE_NAME}...")
table.put_item(Item=clean_carl)
print("SUCCESS: Carl has been reset.")