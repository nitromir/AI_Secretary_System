"""File upload and management endpoints."""

import logging

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from ...utils.files import get_file_storage


router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/v1/files")
async def upload_file(
    file: UploadFile = File(...),
    purpose: str = Form(default="assistants"),
):
    """
    Upload a file for use with chat completions.

    OpenAI-compatible endpoint.
    Files are stored temporarily and can be referenced in messages.
    """
    storage = get_file_storage()

    try:
        info = storage.upload(
            file=file.file,
            filename=file.filename or "unknown",
            content_type=file.content_type or "application/octet-stream",
            purpose=purpose,
        )

        return info.to_dict()

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"File upload error: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload file")


@router.get("/v1/files")
async def list_files(purpose: str | None = None):
    """
    List uploaded files.

    OpenAI-compatible endpoint.
    """
    storage = get_file_storage()
    files = storage.list_files(purpose=purpose)

    return {
        "object": "list",
        "data": [f.to_dict() for f in files],
    }


@router.get("/v1/files/{file_id}")
async def get_file(file_id: str):
    """
    Get file metadata.

    OpenAI-compatible endpoint.
    """
    storage = get_file_storage()
    info = storage.get(file_id)

    if not info:
        raise HTTPException(status_code=404, detail="File not found")

    return info.to_dict()


@router.get("/v1/files/{file_id}/content")
async def get_file_content(file_id: str):
    """
    Get file content.

    OpenAI-compatible endpoint.
    """
    storage = get_file_storage()
    info = storage.get(file_id)

    if not info:
        raise HTTPException(status_code=404, detail="File not found")

    content = storage.get_content(file_id)
    if content is None:
        raise HTTPException(status_code=404, detail="File content not found")

    return Response(
        content=content,
        media_type=info.content_type,
        headers={"Content-Disposition": f'attachment; filename="{info.filename}"'},
    )


@router.delete("/v1/files/{file_id}")
async def delete_file(file_id: str):
    """
    Delete a file.

    OpenAI-compatible endpoint.
    """
    storage = get_file_storage()

    if not storage.delete(file_id):
        raise HTTPException(status_code=404, detail="File not found")

    return {
        "id": file_id,
        "object": "file",
        "deleted": True,
    }
