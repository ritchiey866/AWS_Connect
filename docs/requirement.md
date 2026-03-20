# Requirements: AWS Connect Queue Viewer (Local Demo)

## Goal
Create a small local Python web application with an HTML UI that demonstrates how to:
1. Connect to an AWS Connect instance using `boto3`.
2. Retrieve and display all queues (queue summaries).
3. Retrieve and display detailed information for a selected queue.
4. Persist the retrieved queue data into an AWS database (DynamoDB).

## Functional Requirements
1. AWS Connect connection
   - Use AWS SDK for Python (`boto3`).
   - Region must be configurable (via `AWS_REGION` or `AWS_DEFAULT_REGION`).
2. List queues
   - Call the AWS Connect API operation `ListQueues` for a given Connect instance id.
   - Display all returned queue summaries in the UI (at minimum: `QueueId`, `Name`, `Description`).
   - Support pagination defensively (if the API returns `NextToken`).
3. Queue detail
   - When a user selects a queue from the list, call `DescribeQueue`.
   - Display all returned detail fields in a readable JSON view.
4. Error handling
   - Missing instance id should result in a clear UI message.
   - AWS API errors should be shown as error text returned by the server.
   - DynamoDB writes are best-effort; the UI should still work even if DynamoDB is misconfigured.

## UI Requirements
1. A field to enter `Connect Instance ID`.
2. A “Load Queues” action.
3. A queues table (clickable rows).
4. A details panel that shows queue details as formatted JSON.

## Configuration
The app reads configuration as follows:
- `CONNECT_INSTANCE_ID` (optional default) for the instance id.
- `AWS_REGION` or `AWS_DEFAULT_REGION` for region.
- `QUEUE_DDB_TABLE_NAME` (optional)
  - If set, the app stores queue summaries and queue details in DynamoDB.
- `DYNAMODB_REGION` (optional)
  - Region for DynamoDB. Defaults to `AWS_REGION` / `AWS_DEFAULT_REGION`.
- `QUEUE_DDB_INSTANCE_KEY` (optional, default: `InstanceId`)
- `QUEUE_DDB_QUEUE_KEY` (optional, default: `QueueId`)

The UI can also pass:
- `instance_id` via query parameters.
- optional `region` override via query parameters.

## DynamoDB Table Schema
When persistence is enabled, the app expects a DynamoDB table with:
- Partition key: `InstanceId` (configurable via `QUEUE_DDB_INSTANCE_KEY`)
- Sort key: `QueueId` (configurable via `QUEUE_DDB_QUEUE_KEY`)

Each queue item stores:
- `Name`, `Description`
- `SummaryJson` + `SummaryRetrievedAt`
- `DetailJson` + `DetailRetrievedAt`
- `UpdatedAt`

## Required IAM Permissions
- `connect:ListQueues`
- `connect:DescribeQueue`
- `dynamodb:DescribeTable`
- `dynamodb:CreateTable`
- `dynamodb:UpdateItem`

## Implementation Constraints
- Backend: Flask (simple local web server).
- Frontend: plain HTML + JavaScript (no build tooling required).

## Expected API Usage (Backend)
- `boto3.client("connect", region_name=...)`
- `client.list_queues(InstanceId=...)`
- `client.describe_queue(InstanceId=..., QueueId=...)`
- `boto3.resource("dynamodb").Table(...).update_item(...)`

## Setup and Run
1. Create/activate a local Python environment (Python 3.9+ recommended).
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Configure environment variables in `.env`
   - Update `AWS_REGION` and `CONNECT_INSTANCE_ID`
   - Optionally set `QUEUE_DDB_TABLE_NAME` (and `DYNAMODB_REGION` if different)
   - If you are not using your usual AWS auth method (like `~/.aws/credentials` or SSO), you can also fill in `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`.
4. (Optional) Create the DynamoDB table and enable persistence:
   - Ensure `QUEUE_DDB_TABLE_NAME` is set in `.env`
   - Run: `python scripts/create_dynamodb_table.py`
5. Start the server:
   - `python app.py`
6. Open:
   - `http://127.0.0.1:5000/`

## Non-Goals
- No authentication UI: the AWS SDK uses the standard environment/credential provider chain.
- No contact history / routing logic beyond queue metadata.

## Deliverables
- Working local app (backend + UI).
- Documentation in `docs/requirement.md`, `docs/to-do.md`, and `docs/testing.md`.

