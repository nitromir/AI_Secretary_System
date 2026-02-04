"""Models listing endpoint."""

from fastapi import APIRouter, HTTPException

from ...models import Model, ModelList, create_error
from ...providers import get_all_models


router = APIRouter()


@router.get("/v1/models")
async def list_models() -> ModelList:
    """List available models."""
    models = await get_all_models()
    return ModelList(data=models)


@router.get("/v1/models/{model_id}")
async def get_model(model_id: str) -> Model:
    """Get a specific model."""
    models = await get_all_models()

    for model in models:
        if model.id == model_id:
            return model

    raise HTTPException(
        status_code=404,
        detail=create_error(
            f"Model '{model_id}' not found",
            error_type="not_found_error",
        ).model_dump(),
    )
