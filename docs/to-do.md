# Design + To-Do: AWS Connect Queue Viewer

## Design Overview
The project is a small local Flask application that serves a static HTML UI.

### Components
1. `app.py` (Flask backend)
   - Loads local configuration from `.env` (for local demo).
   - Provides API endpoints:
     - `GET /api/queues` returns queue summaries for an instance.
     - `GET /api/queues/<queue_id>` returns details for a specific queue.
   - Uses `boto3` AWS SDK to call AWS Connect APIs:
     - `list_queues`
     - `describe_queue`
   - Persists queue summaries and details into DynamoDB (best-effort).
   - Converts AWS responses into JSON for the frontend.
2. `templates/index.html` (single-page UI)
   - Input fields for `Connect Instance ID` and optional `AWS Region`.
   - Table for queue summaries with clickable rows.
   - JSON details panel for the selected queue.
3. `static/app.js`
   - Fetches queue list and queue details from the Flask backend.
   - Renders results in the table and JSON panel.
4. `static/styles.css`
   - Basic dark theme styling.
5. `scripts/create_dynamodb_table.py`
   - Creates the DynamoDB table used for queue persistence.

### Data Flow
1. User enters `Connect Instance ID` (or uses `CONNECT_INSTANCE_ID` env var default).
   - The default comes from `.env` (if present) or process environment.
2. UI calls `GET /api/queues?instance_id=...&region=...`.
3. Backend calls AWS Connect `ListQueues` and returns `queues` array.
   - Backend also upserts queue summaries into DynamoDB when `QUEUE_DDB_TABLE_NAME` is configured.
4. UI renders each queue row.
5. User clicks a queue row.
6. UI calls `GET /api/queues/<queue_id>?instance_id=...&region=...`.
7. Backend calls AWS Connect `DescribeQueue`.
8. Backend also upserts queue details into DynamoDB (best-effort).
9. UI renders the response as pretty JSON.

## Implementation Notes
- The backend supports pagination defensively: if the AWS API returns `NextToken`, it keeps calling until exhausted.
- The UI displays `QueueId`, `Name`, and `Description` in the table, and shows the full `DescribeQueue` response for transparency.

## To-Do (Possible Next Enhancements)
1. Add request/response logging (redacting any sensitive values).
2. Add a “refresh” button and preserve selected queue after reload.
3. Add client-side search/filter for queues.
4. Add more table columns (e.g., status fields) once the exact response shape is confirmed in the target environment.
5. Add automated tests with mocked `boto3` (`unittest` + `unittest.mock`), including DynamoDB writes.
6. Add a clearer error mapping for common AWS Connect exceptions (access denied, invalid instance id, throttling).
7. Add a UI indicator for DynamoDB write status/warnings (optional, since writes are best-effort today).

