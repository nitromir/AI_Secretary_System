"""File storage utility for temporary file uploads."""

import logging
import shutil
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from .subprocess import get_sandbox_dir


logger = logging.getLogger(__name__)

# Default directory for uploaded files (inside sandbox for CLI access)
DEFAULT_UPLOAD_DIR = get_sandbox_dir() / "uploads"


@dataclass
class FileInfo:
    """Metadata for an uploaded file."""

    id: str
    filename: str
    path: Path
    size: int
    content_type: str
    created_at: float
    purpose: str = "assistants"

    def to_dict(self) -> dict:
        """Convert to OpenAI-compatible file object."""
        return {
            "id": self.id,
            "object": "file",
            "bytes": self.size,
            "created_at": int(self.created_at),
            "filename": self.filename,
            "purpose": self.purpose,
        }


class FileStorage:
    """Manages temporary file storage for CLI tools."""

    def __init__(
        self,
        upload_dir: Path | None = None,
        max_file_size: int = 100 * 1024 * 1024,  # 100MB
        max_files: int = 100,
        ttl_seconds: int = 3600,  # 1 hour
    ):
        self.upload_dir = upload_dir or DEFAULT_UPLOAD_DIR
        self.max_file_size = max_file_size
        self.max_files = max_files
        self.ttl_seconds = ttl_seconds

        self._files: dict[str, FileInfo] = {}
        self._lock = threading.Lock()

        # Ensure upload directory exists
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"File storage initialized at {self.upload_dir}")

    def upload(
        self,
        file: BinaryIO,
        filename: str,
        content_type: str = "application/octet-stream",
        purpose: str = "assistants",
    ) -> FileInfo:
        """
        Upload a file to temporary storage.

        Args:
            file: File-like object to upload
            filename: Original filename
            content_type: MIME type
            purpose: OpenAI purpose field

        Returns:
            FileInfo with file metadata

        Raises:
            ValueError: If file is too large or storage is full
        """
        # Generate unique ID
        file_id = f"file-{uuid.uuid4().hex[:24]}"

        # Read file content
        content = file.read()
        size = len(content)

        if size > self.max_file_size:
            raise ValueError(f"File too large: {size} bytes (max {self.max_file_size})")

        with self._lock:
            # Check storage limits
            if len(self._files) >= self.max_files:
                # Try to cleanup expired files first
                self._cleanup_expired()
                if len(self._files) >= self.max_files:
                    raise ValueError(
                        f"Storage full: {len(self._files)} files (max {self.max_files})"
                    )

            # Save file to disk
            # Use subdirectory based on file ID for organization
            file_dir = self.upload_dir / file_id
            file_dir.mkdir(parents=True, exist_ok=True)
            file_path = file_dir / filename

            file_path.write_bytes(content)

            # Create file info
            info = FileInfo(
                id=file_id,
                filename=filename,
                path=file_path,
                size=size,
                content_type=content_type,
                created_at=time.time(),
                purpose=purpose,
            )

            self._files[file_id] = info
            logger.info(f"Uploaded file: {file_id} ({filename}, {size} bytes)")

            return info

    def get(self, file_id: str) -> FileInfo | None:
        """Get file info by ID."""
        with self._lock:
            return self._files.get(file_id)

    def get_content(self, file_id: str) -> bytes | None:
        """Get file content by ID."""
        info = self.get(file_id)
        if info and info.path.exists():
            return info.path.read_bytes()
        return None

    def get_text_content(self, file_id: str, encoding: str = "utf-8") -> str | None:
        """Get file content as text."""
        content = self.get_content(file_id)
        if content:
            try:
                return content.decode(encoding)
            except UnicodeDecodeError:
                return None
        return None

    def delete(self, file_id: str) -> bool:
        """Delete a file by ID."""
        with self._lock:
            info = self._files.pop(file_id, None)
            if info:
                # Delete file and its directory
                file_dir = self.upload_dir / file_id
                if file_dir.exists():
                    shutil.rmtree(file_dir)
                logger.info(f"Deleted file: {file_id}")
                return True
            return False

    def list_files(self, purpose: str | None = None) -> list[FileInfo]:
        """List all files, optionally filtered by purpose."""
        with self._lock:
            files = list(self._files.values())
            if purpose:
                files = [f for f in files if f.purpose == purpose]
            return files

    def _cleanup_expired(self) -> int:
        """Remove expired files. Must be called with lock held."""
        now = time.time()
        expired = [
            fid for fid, info in self._files.items() if now - info.created_at > self.ttl_seconds
        ]

        for file_id in expired:
            self._files.pop(file_id)
            file_dir = self.upload_dir / file_id
            if file_dir.exists():
                shutil.rmtree(file_dir)
            logger.debug(f"Cleaned up expired file: {file_id}")

        return len(expired)

    def cleanup_all(self) -> int:
        """Remove all files."""
        with self._lock:
            count = len(self._files)
            self._files.clear()

            # Remove all subdirectories
            if self.upload_dir.exists():
                for item in self.upload_dir.iterdir():
                    if item.is_dir():
                        shutil.rmtree(item)

            logger.info(f"Cleaned up {count} files")
            return count


# Global file storage instance
_storage: FileStorage | None = None


def get_file_storage() -> FileStorage:
    """Get or create global file storage."""
    global _storage
    if _storage is None:
        _storage = FileStorage()
    return _storage
