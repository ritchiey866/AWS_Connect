import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from flask import Flask, jsonify, render_template, request
from dotenv import load_dotenv


# Load configuration from local `.env` (for local demo use).
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_BASE_DIR, ".env"))


def _get_region() -> Optional[str]:
    return os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION")


def _get_default_instance_id() -> Optional[str]:
    return os.getenv("CONNECT_INSTANCE_ID")


def get_connect_client(region_name: Optional[str] = None):
    region = region_name or _get_region()
    if not region:
        raise ValueError(
            "Missing AWS region. Set AWS_REGION or AWS_DEFAULT_REGION."
        )
    return boto3.client("connect", region_name=region)


def list_queues(
    instance_id: str, region_name: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Retrieve all queue summaries for a given AWS Connect instance.
    """
    client = get_connect_client(region_name=region_name)

    # AWS APIs sometimes paginate with NextToken. We support it defensively.
    queues: List[Dict[str, Any]] = []
    next_token: Optional[str] = None

    while True:
        params: Dict[str, Any] = {"InstanceId": instance_id}
        if next_token:
            params["NextToken"] = next_token

        resp = client.list_queues(**params)

        # Prefer QueueSummaryList if present, otherwise fall back to raw keys.
        summary_list = resp.get("QueueSummaryList")
        if isinstance(summary_list, list):
            queues.extend(summary_list)
        else:
            # Keep this fallback lightweight; UI can still show raw response.
            queues.append({"_raw": resp})

        next_token = resp.get("NextToken")
        if not next_token:
            break

    return queues


def describe_queue(
    instance_id: str,
    queue_id: str,
    region_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Retrieve detailed info for a given queue.
    """
    client = get_connect_client(region_name=region_name)
    resp = client.describe_queue(
        InstanceId=instance_id,
        QueueId=queue_id,
    )
    return resp


def _json_safe(obj: Any) -> Any:
    """
    Convert objects that Flask/json may not serialize cleanly.
    """
    try:
        json.dumps(obj)
        return obj
    except TypeError:
        return str(obj)


def _get_ddb_config() -> Dict[str, Optional[str]]:
    """
    DynamoDB persistence config.

    If TABLE name is not set, database writes are disabled (demo still works).
    """
    table_name = os.getenv("QUEUE_DDB_TABLE_NAME")
    region_name = (
        os.getenv("DYNAMODB_REGION")
        or os.getenv("AWS_REGION")
        or os.getenv("AWS_DEFAULT_REGION")
    )
    instance_key = os.getenv("QUEUE_DDB_INSTANCE_KEY", "InstanceId")
    queue_key = os.getenv("QUEUE_DDB_QUEUE_KEY", "QueueId")
    return {
        "table_name": table_name,
        "region_name": region_name,
        "instance_key": instance_key,
        "queue_key": queue_key,
    }


def _get_dynamodb_resource(region_name: Optional[str]):
    region = region_name or _get_region()
    if not region:
        raise ValueError(
            "Missing DynamoDB region. Set DYNAMODB_REGION or AWS_REGION/AWS_DEFAULT_REGION."
        )
    return boto3.resource("dynamodb", region_name=region)


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def upsert_queue_summary_to_ddb(
    instance_id: str,
    queue: Dict[str, Any],
    region_name: Optional[str] = None,
) -> None:
    cfg = _get_ddb_config()
    table_name = cfg["table_name"]
    if not table_name:
        return

    ddb = _get_dynamodb_resource(cfg["region_name"])
    table = ddb.Table(table_name)

    queue_id = queue.get("QueueId") or queue.get(cfg["queue_key"])
    if not queue_id:
        # If list response doesn't include QueueId, we can't store it as keyed item.
        return

    name = queue.get("Name") or ""
    description = queue.get("Description") or ""

    summary_json = json.dumps(queue, default=str, ensure_ascii=False)
    now = _iso_now()

    table.update_item(
        Key={cfg["instance_key"]: instance_id, cfg["queue_key"]: queue_id},
        UpdateExpression=(
            "SET #Name = :name, "
            "#Description = :desc, "
            "#SummaryJson = :summaryJson, "
            "#SummaryRetrievedAt = :retrievedAt, "
            "#UpdatedAt = :updatedAt"
        ),
        ExpressionAttributeNames={
            "#Name": "Name",
            "#Description": "Description",
            "#SummaryJson": "SummaryJson",
            "#SummaryRetrievedAt": "SummaryRetrievedAt",
            "#UpdatedAt": "UpdatedAt",
        },
        ExpressionAttributeValues={
            ":name": name,
            ":desc": description,
            ":summaryJson": summary_json,
            ":retrievedAt": now,
            ":updatedAt": now,
        },
    )


def upsert_queue_detail_to_ddb(
    instance_id: str,
    queue_id: str,
    details: Dict[str, Any],
    region_name: Optional[str] = None,
) -> None:
    cfg = _get_ddb_config()
    table_name = cfg["table_name"]
    if not table_name:
        return

    ddb = _get_dynamodb_resource(cfg["region_name"])
    table = ddb.Table(table_name)

    now = _iso_now()
    detail_json = json.dumps(details, default=str, ensure_ascii=False)

    table.update_item(
        Key={cfg["instance_key"]: instance_id, cfg["queue_key"]: queue_id},
        UpdateExpression=(
            "SET #DetailJson = :detailJson, "
            "#DetailRetrievedAt = :retrievedAt, "
            "#UpdatedAt = :updatedAt"
        ),
        ExpressionAttributeNames={
            "#DetailJson": "DetailJson",
            "#DetailRetrievedAt": "DetailRetrievedAt",
            "#UpdatedAt": "UpdatedAt",
        },
        ExpressionAttributeValues={
            ":detailJson": detail_json,
            ":retrievedAt": now,
            ":updatedAt": now,
        },
    )


app = Flask(__name__)


@app.get("/")
def index():
    default_instance_id = _get_default_instance_id() or ""
    return render_template("index.html", default_instance_id=default_instance_id)


@app.get("/api/queues")
def api_list_queues():
    instance_id = request.args.get("instance_id") or _get_default_instance_id()
    if not instance_id:
        return jsonify(
            {"error": "Missing CONNECT instance id.", "hint": "Set CONNECT_INSTANCE_ID or pass ?instance_id=..."}
        ), 400

    region_name = request.args.get("region") or None
    try:
        queues = list_queues(instance_id=instance_id, region_name=region_name)
        cfg = _get_ddb_config()
        warnings = []
        if cfg.get("table_name") and queues:
            # Best-effort persistence: the demo UI should still work even if DB writes fail.
            for q in queues:
                try:
                    upsert_queue_summary_to_ddb(
                        instance_id=instance_id,
                        queue=q,
                        region_name=region_name,
                    )
                except (ClientError, BotoCoreError) as e:
                    if len(warnings) < 3:
                        warnings.append(str(e))
                    else:
                        break
        payload: Dict[str, Any] = {"instanceId": instance_id, "queues": queues}
        if cfg.get("table_name"):
            payload["dynamoDb"] = {"enabled": True, "warnings": warnings}
        return jsonify(payload)
    except ValueError as e:
        return jsonify({"error": "Bad configuration.", "detail": _json_safe(str(e))}), 500
    except (ClientError, BotoCoreError) as e:
        return jsonify({"error": "AWS Connect API error.", "detail": _json_safe(e)}), 502
    except Exception as e:
        return jsonify({"error": "Unexpected server error.", "detail": _json_safe(e)}), 500


@app.get("/api/queues/<queue_id>")
def api_describe_queue(queue_id: str):
    instance_id = request.args.get("instance_id") or _get_default_instance_id()
    if not instance_id:
        return jsonify(
            {"error": "Missing CONNECT instance id.", "hint": "Set CONNECT_INSTANCE_ID or pass ?instance_id=..."}
        ), 400

    region_name = request.args.get("region") or None
    try:
        details = describe_queue(
            instance_id=instance_id,
            queue_id=queue_id,
            region_name=region_name,
        )
        cfg = _get_ddb_config()
        if cfg.get("table_name"):
            try:
                upsert_queue_detail_to_ddb(
                    instance_id=instance_id,
                    queue_id=queue_id,
                    details=details,
                    region_name=region_name,
                )
            except (ClientError, BotoCoreError):
                # Best-effort only; do not fail the UX when DB isn't writeable.
                pass

        return jsonify(
            {"instanceId": instance_id, "queueId": queue_id, "details": details}
        )
    except (ClientError, BotoCoreError) as e:
        return jsonify({"error": "AWS Connect API error.", "detail": _json_safe(e)}), 502
    except Exception as e:
        return jsonify({"error": "Unexpected server error.", "detail": _json_safe(e)}), 500


if __name__ == "__main__":
    # For local demo use only.
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")), debug=True)

