# app/routers/wiki_rag.py
"""Wiki RAG management router — stats, search, knowledge base CRUD."""

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel

from app.dependencies import get_container
from auth_manager import User, get_current_user, require_not_guest
from db.integration import async_audit_logger, async_knowledge_doc_manager


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/wiki-rag", tags=["wiki-rag"])

WIKI_DIR = Path("wiki-pages")


# ---- Pydantic models ----


class WikiSearchRequest(BaseModel):
    query: str
    top_k: int = 3
    max_chars: int = 1500


class DocumentUpdateRequest(BaseModel):
    title: str | None = None
    content: str | None = None


# ---- Helpers ----


async def _sync_disk_to_db() -> int:
    """Sync wiki-pages/*.md files to knowledge_documents DB table.

    Creates records for files on disk that don't have DB entries yet.
    Returns number of newly synced records.
    """
    if not WIKI_DIR.exists():
        return 0

    synced = 0
    for md_file in sorted(WIKI_DIR.glob("*.md")):
        if md_file.name.startswith("_"):
            continue
        existing = await async_knowledge_doc_manager.get_by_filename(md_file.name)
        if existing:
            continue

        # Count sections (## and ### headers)
        try:
            content = md_file.read_text(encoding="utf-8")
        except Exception:
            continue

        import re

        sections = len(re.findall(r"^#{2,3}\s+.+$", content, re.MULTILINE))
        title = md_file.stem.replace("-", " ").replace("_", " ")

        # Try to extract title from first # header
        first_header = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        if first_header:
            title = first_header.group(1).strip()

        await async_knowledge_doc_manager.create(
            filename=md_file.name,
            title=title,
            source_type="wiki",
            file_size_bytes=md_file.stat().st_size,
            section_count=sections,
        )
        synced += 1

    return synced


def _get_wiki_rag():
    """Get wiki RAG service from container."""
    container = get_container()
    return container.wiki_rag_service


# ---- Endpoints ----


@router.get("/stats")
async def wiki_rag_stats(user: User = Depends(get_current_user)):
    """Get Wiki RAG index statistics and source file list."""
    wiki_rag = _get_wiki_rag()
    if not wiki_rag:
        return {
            "stats": {
                "sections_indexed": 0,
                "files_indexed": 0,
                "unique_tokens": 0,
                "available": False,
            },
            "source_files": [],
        }

    return {
        "stats": wiki_rag.stats,
        "source_files": wiki_rag.list_source_files(),
    }


@router.post("/reload")
async def wiki_rag_reload(user: User = Depends(require_not_guest)):
    """Re-index wiki-pages/ directory."""
    wiki_rag = _get_wiki_rag()
    if not wiki_rag:
        raise HTTPException(status_code=503, detail="Wiki RAG сервис не инициализирован")

    result = wiki_rag.reload(WIKI_DIR)

    await async_audit_logger.log(
        action="reload",
        resource="wiki_rag",
        user_id=user.username,
        details=result,
    )

    return {"status": "ok", **result}


@router.post("/reindex-embeddings")
async def wiki_rag_reindex_embeddings(user: User = Depends(require_not_guest)):
    """Force rebuild all embedding vectors from scratch."""
    wiki_rag = _get_wiki_rag()
    if not wiki_rag:
        raise HTTPException(status_code=503, detail="Wiki RAG сервис не инициализирован")

    result = wiki_rag.reindex_embeddings()

    await async_audit_logger.log(
        action="reindex_embeddings",
        resource="wiki_rag",
        user_id=user.username,
        details=result,
    )

    return {"status": "ok", **result}


@router.post("/search")
async def wiki_rag_search(
    request: WikiSearchRequest,
    user: User = Depends(get_current_user),
):
    """Test search: query → scored results."""
    wiki_rag = _get_wiki_rag()
    if not wiki_rag:
        return {"results": [], "query": request.query}

    results = wiki_rag.search(request.query, top_k=request.top_k)
    return {"results": results, "query": request.query}


@router.get("/documents")
async def list_documents(user: User = Depends(get_current_user)):
    """List all knowledge base documents. Syncs disk → DB on first call."""
    synced = await _sync_disk_to_db()
    documents = await async_knowledge_doc_manager.get_all()
    return {"documents": documents, "synced": synced}


@router.post("/documents/upload")
async def upload_document(
    file: UploadFile,
    user: User = Depends(require_not_guest),
):
    """Upload .md or .txt file to wiki-pages/ and register in DB."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Имя файла не указано")

    # Validate extension
    suffix = Path(file.filename).suffix.lower()
    if suffix not in (".md", ".txt"):
        raise HTTPException(status_code=400, detail="Допустимые форматы: .md, .txt")

    # Ensure .md extension for storage
    filename = file.filename if suffix == ".md" else Path(file.filename).stem + ".md"

    # Check duplicate
    existing = await async_knowledge_doc_manager.get_by_filename(filename)
    if existing:
        raise HTTPException(status_code=409, detail=f"Файл {filename} уже существует")

    # Read content
    content_bytes = await file.read()
    content = content_bytes.decode("utf-8")

    # Write to wiki-pages/
    WIKI_DIR.mkdir(exist_ok=True)
    target = WIKI_DIR / filename
    target.write_text(content, encoding="utf-8")

    # Count sections
    import re

    sections = len(re.findall(r"^#{2,3}\s+.+$", content, re.MULTILINE))

    # Extract title
    title = Path(filename).stem.replace("-", " ").replace("_", " ")
    first_header = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if first_header:
        title = first_header.group(1).strip()

    # Create DB record
    owner_id = None if user.role == "admin" else user.id
    doc = await async_knowledge_doc_manager.create(
        filename=filename,
        title=title,
        source_type="manual",
        file_size_bytes=len(content_bytes),
        section_count=sections,
        owner_id=owner_id,
    )

    # Re-index
    wiki_rag = _get_wiki_rag()
    if wiki_rag:
        wiki_rag.reload(WIKI_DIR)

    await async_audit_logger.log(
        action="upload",
        resource="wiki_rag_document",
        resource_id=filename,
        user_id=user.username,
        details={"size": len(content_bytes), "sections": sections},
    )

    return {"status": "ok", "document": doc}


@router.get("/documents/{doc_id}")
async def get_document(doc_id: int, user: User = Depends(get_current_user)):
    """Get document metadata + content preview."""
    doc = await async_knowledge_doc_manager.get_by_id(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Документ не найден")

    # Read content preview from disk
    content_preview = ""
    file_path = WIKI_DIR / doc["filename"]
    if file_path.exists():
        try:
            full_content = file_path.read_text(encoding="utf-8")
            content_preview = full_content[:2000]
        except Exception:
            pass

    return {"document": doc, "content_preview": content_preview}


@router.put("/documents/{doc_id}")
async def update_document(
    doc_id: int,
    request: DocumentUpdateRequest,
    user: User = Depends(require_not_guest),
):
    """Update document title and/or content."""
    doc = await async_knowledge_doc_manager.get_by_id(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Документ не найден")

    # Update file content if provided
    if request.content is not None:
        file_path = WIKI_DIR / doc["filename"]
        file_path.write_text(request.content, encoding="utf-8")

        import re

        sections = len(re.findall(r"^#{2,3}\s+.+$", request.content, re.MULTILINE))
        await async_knowledge_doc_manager.update(
            doc_id,
            title=request.title,
            file_size_bytes=len(request.content.encode("utf-8")),
            section_count=sections,
        )

        # Re-index after content change
        wiki_rag = _get_wiki_rag()
        if wiki_rag:
            wiki_rag.reload(WIKI_DIR)
    elif request.title is not None:
        await async_knowledge_doc_manager.update(doc_id, title=request.title)

    updated_doc = await async_knowledge_doc_manager.get_by_id(doc_id)

    await async_audit_logger.log(
        action="update",
        resource="wiki_rag_document",
        resource_id=str(doc_id),
        user_id=user.username,
    )

    return {"status": "ok", "document": updated_doc}


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: int, user: User = Depends(require_not_guest)):
    """Delete document from disk and DB, re-index."""
    doc = await async_knowledge_doc_manager.get_by_id(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Документ не найден")

    # Delete file from disk
    file_path = WIKI_DIR / doc["filename"]
    if file_path.exists():
        file_path.unlink()

    # Delete DB record
    await async_knowledge_doc_manager.delete(doc_id)

    # Re-index
    wiki_rag = _get_wiki_rag()
    if wiki_rag:
        wiki_rag.reload(WIKI_DIR)

    await async_audit_logger.log(
        action="delete",
        resource="wiki_rag_document",
        resource_id=doc["filename"],
        user_id=user.username,
    )

    return {"status": "ok", "deleted": doc["filename"]}
