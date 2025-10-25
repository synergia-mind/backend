from app.core.logging import get_logger
from app.services.model import ModelService
from app.api.depends import SessionDep
from app.models import ModelCreate, ModelUpdate, ModelPublic, MessageResponse

from fastapi import APIRouter, HTTPException, status
from uuid import UUID


router = APIRouter()

logger = get_logger(__name__)


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=ModelPublic)
async def create_model(model_data: ModelCreate, session: SessionDep):
    """
    Create a new AI model.
    
    Args:
        model_data: Model creation data (name, provider, price_per_million_tokens, is_enabled)
        
    Returns:
        Created model
        
    Raises:
        HTTPException: If a model with the same name already exists
    """
    service = ModelService(session)
    try:
        model = service.create_model(model_data)
        logger.info(f"Created model: {model.name} (ID: {model.id})")
        return model
    except ValueError as e:
        logger.warning(f"Failed to create model: {str(e)}")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.get("/", response_model=list[ModelPublic])
async def get_all_models(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    enabled_only: bool = False
):
    """
    Get all models with pagination.
    
    Args:
        skip: Number of records to skip (default: 0)
        limit: Maximum number of records to return (default: 100)
        enabled_only: If True, only return enabled models (default: False)
        
    Returns:
        List of models
    """
    service = ModelService(session)
    models = service.get_all_models(skip=skip, limit=limit, enabled_only=enabled_only)
    logger.info(f"Retrieved {len(models)} models (skip={skip}, limit={limit}, enabled_only={enabled_only})")
    return models


@router.get("/enabled", response_model=list[ModelPublic])
async def get_enabled_models(session: SessionDep, skip: int = 0, limit: int = 100):
    """
    Get all enabled models.
    
    Args:
        skip: Number of records to skip (default: 0)
        limit: Maximum number of records to return (default: 100)
        
    Returns:
        List of enabled models
    """
    service = ModelService(session)
    models = service.get_enabled_models(skip=skip, limit=limit)
    logger.info(f"Retrieved {len(models)} enabled models")
    return models


@router.get("/providers", response_model=list[str])
async def get_available_providers(session: SessionDep):
    """
    Get a list of unique providers from all models.
    
    Returns:
        List of unique provider names
    """
    service = ModelService(session)
    providers = service.get_available_providers()
    logger.info(f"Retrieved {len(providers)} unique providers")
    return providers


@router.get("/provider/{provider}", response_model=list[ModelPublic])
async def get_models_by_provider(provider: str, session: SessionDep):
    """
    Get all models by provider.
    
    Args:
        provider: Provider name
        
    Returns:
        List of models from the specified provider
    """
    service = ModelService(session)
    models = service.get_models_by_provider(provider)
    logger.info(f"Retrieved {len(models)} models for provider: {provider}")
    return models


@router.get("/count", response_model=dict)
async def count_models(session: SessionDep, enabled_only: bool = False):
    """
    Count total models.
    
    Args:
        enabled_only: If True, only count enabled models (default: False)
        
    Returns:
        Dictionary with count
    """
    service = ModelService(session)
    count = service.count_models(enabled_only=enabled_only)
    logger.info(f"Model count: {count} (enabled_only={enabled_only})")
    return {"count": count}


@router.get("/name/{name}", response_model=ModelPublic)
async def get_model_by_name(name: str, session: SessionDep):
    """
    Get a model by name.
    
    Args:
        name: Model name
        
    Returns:
        Model with the specified name
        
    Raises:
        HTTPException: If model not found
    """
    service = ModelService(session)
    model = service.get_model_by_name(name)
    if not model:
        logger.warning(f"Model not found with name: {name}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Model with name '{name}' not found")
    logger.info(f"Retrieved model by name: {name}")
    return model


@router.get("/{model_id}", response_model=ModelPublic)
async def get_model_by_id(model_id: UUID, session: SessionDep):
    """
    Get a model by ID.
    
    Args:
        model_id: Model UUID
        
    Returns:
        Model with the specified ID
        
    Raises:
        HTTPException: If model not found
    """
    service = ModelService(session)
    model = service.get_model_by_id(model_id)
    if not model:
        logger.warning(f"Model not found with ID: {model_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")
    logger.info(f"Retrieved model: {model.name} (ID: {model_id})")
    return model


@router.put("/{model_id}", response_model=ModelPublic)
async def update_model(model_id: UUID, model_data: ModelUpdate, session: SessionDep):
    """
    Update a model.
    
    Args:
        model_id: Model UUID
        model_data: Model update data
        
    Returns:
        Updated model
        
    Raises:
        HTTPException: If model not found or name conflict
    """
    service = ModelService(session)
    try:
        model = service.update_model(model_id, model_data)
        if not model:
            logger.warning(f"Model not found for update: {model_id}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")
        logger.info(f"Updated model: {model.name} (ID: {model_id})")
        return model
    except ValueError as e:
        logger.warning(f"Failed to update model {model_id}: {str(e)}")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.patch("/{model_id}/toggle", response_model=ModelPublic)
async def toggle_model_enabled(model_id: UUID, session: SessionDep):
    """
    Toggle the enabled status of a model.
    
    Args:
        model_id: Model UUID
        
    Returns:
        Updated model with toggled enabled status
        
    Raises:
        HTTPException: If model not found
    """
    service = ModelService(session)
    model = service.toggle_model_enabled(model_id)
    if not model:
        logger.warning(f"Model not found for toggle: {model_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")
    logger.info(f"Toggled model enabled status: {model.name} (ID: {model_id}, enabled={model.is_enabled})")
    return model


@router.patch("/{model_id}/enable", response_model=ModelPublic)
async def enable_model(model_id: UUID, session: SessionDep):
    """
    Enable a model (set is_enabled to True).
    
    Args:
        model_id: Model UUID
        
    Returns:
        Updated model with enabled status
        
    Raises:
        HTTPException: If model not found
    """
    service = ModelService(session)
    model = service.enable_model(model_id)
    if not model:
        logger.warning(f"Model not found for enable: {model_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")
    logger.info(f"Enabled model: {model.name} (ID: {model_id})")
    return model


@router.patch("/{model_id}/disable", response_model=ModelPublic)
async def disable_model(model_id: UUID, session: SessionDep):
    """
    Disable a model (set is_enabled to False).
    
    Args:
        model_id: Model UUID
        
    Returns:
        Updated model with disabled status
        
    Raises:
        HTTPException: If model not found
    """
    service = ModelService(session)
    model = service.disable_model(model_id)
    if not model:
        logger.warning(f"Model not found for disable: {model_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")
    logger.info(f"Disabled model: {model.name} (ID: {model_id})")
    return model


@router.delete("/{model_id}", status_code=status.HTTP_200_OK, response_model=MessageResponse)
async def delete_model(model_id: UUID, session: SessionDep):
    """
    Delete a model.
    
    Args:
        model_id: Model UUID
        
    Returns:
        Success message
        
    Raises:
        HTTPException: If model not found
    """
    service = ModelService(session)
    deleted = service.delete_model(model_id)
    if not deleted:
        logger.warning(f"Model not found for deletion: {model_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")
    logger.info(f"Deleted model with ID: {model_id}")
    return MessageResponse(message="Model deleted successfully")