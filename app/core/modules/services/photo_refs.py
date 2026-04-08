from __future__ import annotations

import hashlib
import json
from pathlib import Path


PHOTO_REF_PLATFORMS = ("tg", "vk")


def _default_payload() -> dict:
    return {
        "signature": "",
        "files": [],
        "tg": {},
        "vk": {},
    }


def _normalize_platform_refs(raw_value) -> dict[str, str]:
    if not isinstance(raw_value, dict):
        return {}
    normalized: dict[str, str] = {}
    for key, value in raw_value.items():
        if not key or not value:
            continue
        normalized[str(key)] = str(value)
    return normalized


def parse_service_photo_refs(raw_value: str | None) -> dict:
    if not raw_value:
        return _default_payload()

    try:
        payload = json.loads(raw_value)
    except (TypeError, json.JSONDecodeError):
        return _default_payload()

    if not isinstance(payload, dict):
        return _default_payload()

    normalized = _default_payload()
    normalized["signature"] = str(payload.get("signature") or "")
    files = payload.get("files")
    if isinstance(files, list):
        normalized["files"] = [str(item) for item in files if item]

    for platform in PHOTO_REF_PLATFORMS:
        normalized[platform] = _normalize_platform_refs(payload.get(platform))

    return normalized


def build_service_photo_signature(photo_paths: list[Path]) -> str:
    parts: list[str] = []
    for path in sorted(photo_paths, key=lambda item: item.name.lower()):
        stat = path.stat()
        parts.append(f"{path.name}|{stat.st_size}|{stat.st_mtime_ns}")
    payload = "\n".join(parts).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def get_platform_photo_refs(
    raw_value: str | None,
    platform: str,
    photo_paths: list[Path],
) -> tuple[str, dict[str, str]]:
    if platform not in PHOTO_REF_PLATFORMS:
        raise ValueError(f"Unsupported photo refs platform: {platform}")

    signature = build_service_photo_signature(photo_paths)
    payload = parse_service_photo_refs(raw_value)
    if payload.get("signature") != signature:
        return signature, {}

    current_names = {path.name for path in photo_paths}
    platform_refs = payload.get(platform, {})
    if not isinstance(platform_refs, dict):
        return signature, {}

    return signature, {
        name: ref
        for name, ref in platform_refs.items()
        if name in current_names and ref
    }


def update_platform_photo_refs(
    raw_value: str | None,
    platform: str,
    photo_paths: list[Path],
    refs_by_name: dict[str, str],
) -> str:
    if platform not in PHOTO_REF_PLATFORMS:
        raise ValueError(f"Unsupported photo refs platform: {platform}")

    signature = build_service_photo_signature(photo_paths)
    payload = parse_service_photo_refs(raw_value)
    current_names = [path.name for path in sorted(photo_paths, key=lambda item: item.name.lower())]
    current_name_set = set(current_names)

    if payload.get("signature") != signature:
        payload = _default_payload()

    payload["signature"] = signature
    payload["files"] = current_names

    for platform_name in PHOTO_REF_PLATFORMS:
        payload[platform_name] = {
            name: ref
            for name, ref in _normalize_platform_refs(payload.get(platform_name)).items()
            if name in current_name_set
        }

    platform_refs = payload.setdefault(platform, {})
    for name, ref in refs_by_name.items():
        if name in current_name_set and ref:
            platform_refs[name] = str(ref)

    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
