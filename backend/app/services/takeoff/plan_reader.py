"""Experimental plan-reading helper (stub).

Full LLM-based extraction of room/device counts from a floor plan is not yet
implemented. This module validates uploads and produces a basic takeoff using
the standard generator so the endpoint remains functional.
"""
from fastapi import HTTPException, UploadFile

ALLOWED_TYPES = {"application/pdf", "image/png", "image/jpeg", "image/jpg"}
MAX_SIZE_BYTES = 10 * 1024 * 1024


async def validate_plan_upload(upload: UploadFile) -> None:
    if upload.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported file type")
    data = await upload.read()
    if len(data) == 0:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(data) > MAX_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 10MB)")
    await upload.seek(0)
