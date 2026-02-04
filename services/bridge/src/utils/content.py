"""Content extraction utilities for multi-part messages."""

import base64
import logging
import uuid
from typing import Any

from .files import get_file_storage
from .subprocess import get_sandbox_dir


logger = logging.getLogger(__name__)


def extract_content(content: str | list[dict[str, Any]]) -> str:
    """
    Extract text content from message, handling files and images securely.

    Files are referenced by path so CLI tools can read them natively.
    This supports any file type: images, PDFs, Office docs, videos, etc.

    Security measures:
    - Files must be within our upload directory (path traversal prevention)
    - Base64 data is decoded and saved to secure storage
    - Size limits enforced (50MB max)
    - External URLs are referenced but not downloaded

    Args:
        content: String or list of content parts

    Returns:
        Combined text content with file path references
    """
    if isinstance(content, str):
        return content

    parts = []
    file_storage = get_file_storage()

    for part in content:
        part_type = part.get("type", "text")

        if part_type == "text":
            parts.append(part.get("text", ""))

        elif part_type == "file":
            # Pass file path to CLI - let LLM read it natively
            file_id = part.get("file_id", "")
            if file_id:
                file_info = file_storage.get(file_id)
                if file_info and file_info.path.exists():
                    # Security: Verify file is within our upload directory
                    try:
                        file_path = file_info.path.resolve()
                        upload_dir = file_storage.upload_dir.resolve()
                        # Check path is within upload directory (prevent traversal)
                        file_path.relative_to(upload_dir)
                        # Reference the file by path - CLI tools can read various formats
                        parts.append(f"[Attached file: {file_path}]")
                    except ValueError:
                        # Path is outside upload directory - security violation
                        logger.warning(f"Security: File path outside upload dir: {file_info.path}")
                        parts.append("[File access denied]")
                else:
                    parts.append(f"[File {file_id} not found]")

        elif part_type == "image_url":
            # Handle base64 data URLs (images, PDFs, videos, etc.)
            url = part.get("image_url", {}).get("url", "")
            if url.startswith("data:"):
                try:
                    # Parse data URL: data:mime/type;base64,xxxx
                    header, b64_data = url.split(",", 1)
                    mime_type = (
                        header.split(":")[1].split(";")[0]
                        if ":" in header
                        else "application/octet-stream"
                    )

                    # Get extension from mime type
                    ext_map = {
                        "image/png": "png",
                        "image/jpeg": "jpg",
                        "image/gif": "gif",
                        "image/webp": "webp",
                        "image/svg+xml": "svg",
                        "image/bmp": "bmp",
                        "application/pdf": "pdf",
                        "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
                        "application/vnd.ms-powerpoint": "ppt",
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
                        "application/msword": "doc",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
                        "application/vnd.ms-excel": "xls",
                        "video/mp4": "mp4",
                        "video/webm": "webm",
                        "video/quicktime": "mov",
                        "audio/mpeg": "mp3",
                        "audio/wav": "wav",
                        "text/plain": "txt",
                        "text/csv": "csv",
                    }
                    ext = ext_map.get(
                        mime_type, mime_type.split("/")[-1] if "/" in mime_type else "bin"
                    )

                    # Decode and validate size (max 50MB)
                    file_data = base64.b64decode(b64_data)
                    if len(file_data) > 50 * 1024 * 1024:
                        parts.append("[Attachment: too large (max 50MB)]")
                        continue

                    # Save to sandbox directory so CLI tools can access it
                    attach_id = f"attach-{uuid.uuid4().hex[:12]}"
                    attach_dir = get_sandbox_dir() / attach_id
                    attach_dir.mkdir(parents=True, exist_ok=True)
                    file_path = attach_dir / f"attachment.{ext}"
                    file_path.write_bytes(file_data)
                    parts.append(f"[Attached file: {file_path}]")
                except Exception as e:
                    logger.warning(f"Failed to process base64 data: {e}")
                    parts.append("[Attachment: failed to process]")
            else:
                # External URLs - just reference, don't download (security)
                parts.append(f"[External URL: {url}]")

    return "\n".join(parts)
