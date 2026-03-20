import json
import os
from typing import Dict, Optional

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv


# Load configuration from local `.env` (for local demo use).
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_BASE_DIR, ".env"))


def _get_region() -> str:
    region = os.getenv("DYNAMODB_REGION") or os.getenv("AWS_REGION") or os.getenv(
        "AWS_DEFAULT_REGION"
    )
    if not region:
        raise ValueError(
            "Missing region. Set DYNAMODB_REGION or AWS_REGION/AWS_DEFAULT_REGION."
        )
    return region


def _get_table_name() -> str:
    return os.getenv("QUEUE_DDB_TABLE_NAME", "connect-queue-viewer")


def create_table_if_not_exists(
    dynamodb, table_name: str, instance_key: str, queue_key: str
) -> None:
    try:
        existing = dynamodb.describe_table(TableName=table_name)
        print(f"Table already exists: {existing['Table']['TableName']}")
        return
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") != "ResourceNotFoundException":
            raise

    print(f"Creating DynamoDB table: {table_name}")
    dynamodb.create_table(
        TableName=table_name,
        KeySchema=[
            {"AttributeName": instance_key, "KeyType": "HASH"},
            {"AttributeName": queue_key, "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": instance_key, "AttributeType": "S"},
            {"AttributeName": queue_key, "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )

    # Wait until the table is active.
    waiter = dynamodb.meta.client.get_waiter("table_exists")
    waiter.wait(TableName=table_name)
    print("DynamoDB table is active.")


def main() -> None:
    region = _get_region()
    table_name = _get_table_name()

    # Keep these stable because app.py hard-codes them.
    instance_key = os.getenv("QUEUE_DDB_INSTANCE_KEY", "InstanceId")
    queue_key = os.getenv("QUEUE_DDB_QUEUE_KEY", "QueueId")

    session = boto3.session.Session(region_name=region)
    dynamodb = session.resource("dynamodb")

    create_table_if_not_exists(
        dynamodb=dynamodb,
        table_name=table_name,
        instance_key=instance_key,
        queue_key=queue_key,
    )

    # Print a small summary so it is easy to verify from logs.
    print(
        json.dumps(
            {
                "region": region,
                "tableName": table_name,
                "partitionKey": instance_key,
                "sortKey": queue_key,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

