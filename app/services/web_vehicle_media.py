from __future__ import annotations

import base64
import binascii
import logging
import re
from dataclasses import dataclass

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError

from app.core.config import settings

logger = logging.getLogger(__name__)

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")
_DATA_URL = re.compile(r"^data:([^;]+);base64,(.+)$", re.DOTALL | re.IGNORECASE)


class WebVehicleMediaError(Exception):
    pass


@dataclass(frozen=True)
class ImageUpload:
    filename: str
    content_type: str
    data: str


def _require_bucket() -> str:
    bucket = (settings.web_vehicles_s3_bucket or "").strip()
    if not bucket:
        raise WebVehicleMediaError("WEB_VEHICLES_S3_BUCKET is not configured")
    return bucket


def _prefix() -> str:
    return (settings.web_vehicles_s3_prefix or "images/stock").strip().strip("/")


def sanitize_filename(filename: str) -> str:
    name = filename.strip().replace("\\", "/").split("/")[-1]
    name = _SAFE_NAME.sub("-", name).strip(".-")
    return name or "image.bin"


def decode_image_payload(data: str, content_type: str | None = None) -> tuple[bytes, str]:
    raw = data.strip()
    match = _DATA_URL.match(raw)
    if match:
        return base64.b64decode(match.group(2), validate=False), match.group(1) or (
            content_type or "application/octet-stream"
        )
    try:
        return base64.b64decode(raw, validate=False), content_type or "application/octet-stream"
    except (binascii.Error, ValueError) as exc:
        raise WebVehicleMediaError("Invalid base64 image payload") from exc


def is_existing_stock_key(value: str) -> bool:
    key = value.strip().lstrip("/")
    return key.startswith(f"{_prefix()}/")


def build_object_key(uid: int, filename: str, index: int) -> str:
    safe = sanitize_filename(filename)
    if "." not in safe:
        safe = f"{safe}-{index}.bin"
    else:
        stem, ext = safe.rsplit(".", 1)
        safe = f"{stem or 'image'}-{index}.{ext}"
    return f"{_prefix()}/{uid}/{safe}"


def _s3_client():
    return boto3.client(
        "s3",
        region_name=settings.aws_region,
        endpoint_url=f"https://s3.{settings.aws_region}.amazonaws.com",
        config=Config(signature_version="s3v4"),
    )


def upload_image_bytes(key: str, body: bytes, content_type: str) -> str:
    bucket = _require_bucket()
    client = _s3_client()
    try:
        client.put_object(
            Bucket=bucket,
            Key=key,
            Body=body,
            ContentType=content_type,
        )
    except NoCredentialsError as exc:
        logger.exception("AWS credentials missing for s3://%s/%s", bucket, key)
        raise WebVehicleMediaError(
            "AWS credentials not configured for S3 uploads "
            "(set AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY or mount ~/.aws into the API container)"
        ) from exc
    except (BotoCoreError, ClientError) as exc:
        logger.exception("Failed to upload web vehicle image to s3://%s/%s", bucket, key)
        raise WebVehicleMediaError(f"Failed to upload image to S3: {key}") from exc
    return key


def public_urls_for_keys(keys: list[str] | None) -> list[str]:
    """Browser-reachable URLs for stock keys (CDN base or S3 presigned GET)."""
    if not keys:
        return []

    cleaned = [key.strip().lstrip("/") for key in keys if key and key.strip()]
    if not cleaned:
        return []

    base = (settings.web_vehicles_public_media_base_url or "").strip().rstrip("/")
    if base:
        return [f"{base}/{key}" for key in cleaned]

    bucket = (settings.web_vehicles_s3_bucket or "").strip()
    if not bucket:
        return [f"/{key}" for key in cleaned]

    client = _s3_client()
    expires = max(60, int(settings.web_vehicles_s3_presign_expires or 3600))
    urls: list[str] = []
    try:
        for key in cleaned:
            urls.append(
                client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": bucket, "Key": key},
                    ExpiresIn=expires,
                )
            )
    except NoCredentialsError:
        logger.warning("Cannot presign web vehicle images; returning relative keys")
        return [f"/{key}" for key in cleaned]
    except (BotoCoreError, ClientError):
        logger.exception("Failed to presign web vehicle image URLs")
        return [f"/{key}" for key in cleaned]
    return urls


def resolve_images_for_vehicle(uid: int, images: list[str | ImageUpload] | None) -> list[str]:
    """Turn path keys + upload payloads into persisted S3 keys. Uploads always for binary payloads."""
    if not images:
        return []

    resolved: list[str] = []
    upload_index = 0
    for item in images:
        if isinstance(item, str):
            value = item.strip()
            if not value:
                continue
            if is_existing_stock_key(value):
                resolved.append(value.lstrip("/"))
                continue
            # Treat bare strings as data URLs / base64 when they look like uploads.
            if value.startswith("data:") or len(value) > 256:
                body, content_type = decode_image_payload(value)
                upload_index += 1
                key = build_object_key(uid, f"image-{upload_index}.bin", upload_index)
                resolved.append(upload_image_bytes(key, body, content_type))
                continue
            raise WebVehicleMediaError(
                f"Image '{value}' is not an existing stock key and is not an upload payload"
            )

        upload_index += 1
        body, content_type = decode_image_payload(item.data, item.content_type)
        key = build_object_key(uid, item.filename, upload_index)
        resolved.append(upload_image_bytes(key, body, content_type))
    return resolved
