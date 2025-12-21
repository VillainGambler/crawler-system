import boto3
import os
from dotenv import load_dotenv
from botocore.exceptions import ClientError

# Load environment variables
load_dotenv()

REGION = os.getenv("AWS_REGION", "us-east-1")
TABLE_NAME = os.getenv("DYNAMODB_TABLE", "crawler-system-data")

# Connect to DynamoDB
dynamodb = boto3.resource("dynamodb", region_name=REGION)
table = dynamodb.Table(TABLE_NAME)

def get_character(character_id: str):
    """
    Fetch a character by ID.
    """
    try:
        response = table.get_item(
            Key={
                'pk': 'CRAWL#101',
                'sk': f'PLAYER#{character_id}'
            }
        )
        return response.get('Item')
    except ClientError as e:
        print(f"Error fetching character: {e.response['Error']['Message']}")
        return None

def create_character(character_data: dict):
    """
    Save or Overwrite a character.
    """
    # Add the partition keys required for our Single Table Design
    character_data['pk'] = 'CRAWL#101'
    character_data['sk'] = f"PLAYER#{character_data['id']}"
    
    try:
        table.put_item(Item=character_data)
        return True
    except ClientError as e:
        print(f"Error saving character: {e.response['Error']['Message']}")
        return False

def update_hp(character_id: str, amount: int):
    """
    Atomically updates HP.
    amount: positive to heal, negative to damage.
    """
    try:
        response = table.update_item(
            Key={'pk': 'CRAWL#101', 'sk': f'PLAYER#{character_id}'},
            UpdateExpression="SET hp.#c = hp.#c + :val",
            ExpressionAttributeNames={
                "#c": "current"
            },
            ExpressionAttributeValues={
                ':val': amount
            },
            ReturnValues="ALL_NEW"  # <--- CHANGED FROM UPDATED_NEW
        )
        return response.get('Attributes')
    except ClientError as e:
        print(f"Error updating HP: {e.response['Error']['Message']}")
        return None