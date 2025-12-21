# 1. The Provider
# This tells Terraform we are talking to AWS.
provider "aws" {
  region = "us-east-1"  # Or your chosen region (e.g., us-east-2)
}

# 2. The Resource (DynamoDB Table)
resource "aws_dynamodb_table" "crawler_table" {
  name         = "crawler-system-data"
  billing_mode = "PAY_PER_REQUEST" # Serverless billing (Save money!)
  
  # The Primary Key (Partition Key)
  hash_key     = "pk"
  
  # The Sort Key (Range Key)
  range_key    = "sk"

  # Attribute Definitions (Only keys need to be defined here)
  attribute {
    name = "pk"
    type = "S" # String
  }

  attribute {
    name = "sk"
    type = "S" # String
  }

  # Security: Encrypt data at rest using AWS owned keys (Default, but good to be explicit)
  server_side_encryption {
    enabled = true
  }

  # Point-in-Time Recovery (Backup) - Crucial for "Oops" moments
  point_in_time_recovery {
    enabled = true
  }

  tags = {
    Name        = "CrawlerSystemTable"
    Environment = "Dev"
    Project     = "CrawlerSystem"
  }
}