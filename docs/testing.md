# Testing: AWS Connect Queue Viewer

## Prerequisites
1. An AWS account with AWS Connect enabled.
2. Permission to call (at minimum):
   - `connect:ListQueues`
   - `connect:DescribeQueue`
   - If you enable DynamoDB persistence (`QUEUE_DDB_TABLE_NAME` set):
     - `dynamodb:UpdateItem`
     - (and `dynamodb:CreateTable` / `dynamodb:DescribeTable` if you run the table creation script)
3. A valid AWS Connect instance id.

## Manual Test Plan
1. Setup environment variables
   - Fill in `AWS_REGION` and `CONNECT_INSTANCE_ID` in `.env`
   - Ensure AWS credentials are available (for example via `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`, `~/.aws/credentials`, SSO, etc.)
2. Start the server
   - Run the Flask app locally.
3. Load the UI
   - Open `http://127.0.0.1:5000/`.
4. Load queues (happy path)
   - Enter `Connect Instance ID` (if not already present).
   - Click “Load Queues”.
   - Verify:
     - Table is populated with rows.
     - Clicking a queue row loads details.
     - Details panel shows formatted JSON.
5. Error: missing instance id
   - Leave instance id blank and click “Load Queues”.
   - Verify a clear UI error message.
6. Error: wrong instance id / permissions
   - Enter an invalid instance id or revoke permissions.
   - Verify the UI displays an error returned from the backend.
7. Data shape sanity
   - Confirm table fields (`QueueId`, `Name`, `Description`) are populated.
   - If they appear blank, validate the UI fallback behavior against the raw AWS response.
8. DynamoDB persistence (if enabled)
   - Set `QUEUE_DDB_TABLE_NAME` in `.env` and (optionally) run `python scripts/create_dynamodb_table.py`.
   - After clicking “Load Queues”, verify each queue creates/updates an item in DynamoDB.
   - After clicking a queue row, verify that queue detail fields are added/updated in that same DynamoDB item.

## Suggested Automated Tests (Optional)
Automated tests can be added using `unittest.mock` to mock the `boto3.client("connect")` calls:
1. Test `list_queues()` pagination handling
   - Mock `list_queues` to return a `NextToken` on first call and none on second call.
   - Verify the function returns both pages.
2. Test `describe_queue()` pass-through
   - Mock `describe_queue` to return a fixed payload.
   - Verify the API endpoint returns that payload under `details`.
3. Test Flask routes
   - Use Flask’s test client.
   - Mock the AWS functions to avoid real AWS calls.

## What “Pass” Means
- UI successfully loads and displays queue summaries for a real Connect instance.
- UI successfully fetches and displays detailed queue data for a selected queue.
- Errors (missing config, AWS failures) are handled gracefully without server crashes.

