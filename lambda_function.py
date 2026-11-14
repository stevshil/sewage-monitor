import asyncio
import os
from pathlib import Path

import boto3

from get_data import get_data


def lambda_handler(event, context):
    bucket = os.environ.get("S3_BUCKET")
    if not bucket:
        raise ValueError("S3_BUCKET must be configured")

    key = os.environ.get("S3_KEY", "sewage.json")
    if not key:
        raise ValueError("S3_KEY must not be empty")

    work_dir = Path("/tmp/sewage-monitor")
    download_dir = work_dir / "downloads"
    report_dir = work_dir / "reports"

    asyncio.run(get_data(str(download_dir), str(report_dir)))

    json_path = report_dir / "sewage.json"
    if not json_path.is_file():
        raise FileNotFoundError(f"Sewage report was not created: {json_path}")

    boto3.client("s3").upload_file(
        str(json_path),
        bucket,
        key,
        ExtraArgs={"ContentType": "application/json"},
    )

    return {"bucket": bucket, "key": key}
