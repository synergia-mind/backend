from typing import Optional
from uuid import UUID
from sqlmodel import Session

from app.repositories.model import ModelRepository
from app.models import Model, ModelCreate, ModelUpdate, ModelPublic


class ModelService:
    """Service layer for Model business logic."""
    
    def __init__(self, session: Session):
        self.repository = ModelRepository(session)
    
    def create_model(self, model_data: ModelCreate) -> ModelPublic:
        """
        Create a new model.
        
        Args:
            model_data: Model creation data
            
        Returns:
            Created model as ModelPublic
            
        Raises:
            ValueError: If a model with the same name already exists
        """
        # Check if model with same name already exists
        existing_model = self.repository.get_by_name(model_data.name)
        if existing_model:
            raise ValueError(f"Model with name '{model_data.name}' already exists")
        
        model = self.repository.create(model_data)
        return ModelPublic.model_validate(model)
    
    def get_model_by_id(self, model_id: UUID) -> Optional[ModelPublic]:
        """
        Get a model by ID.
        
        Args:
            model_id: Model UUID
            
        Returns:
            ModelPublic instance or None if not found
        """
        model = self.repository.get_by_id(model_id)
        if not model:
            return None
        return ModelPublic.model_validate(model)
    
    def get_model_by_name(self, name: str) -> Optional[ModelPublic]:
        """
        Get a model by name.
        
        Args:
            name: Model name
            
        Returns:
            ModelPublic instance or None if not found
        """
        model = self.repository.get_by_name(name)
        if not model:
            return None
        return ModelPublic.model_validate(model)
    
    def get_all_models(
        self,
        skip: int = 0,
        limit: int = 100,
        enabled_only: bool = False
    ) -> list[ModelPublic]:
        """
        Get all models with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            enabled_only: If True, only return enabled models
            
        Returns:
            List of ModelPublic instances
        """
        models = self.repository.get_all(skip=skip, limit=limit, enabled_only=enabled_only)
        return [ModelPublic.model_validate(model) for model in models]
    
    def get_models_by_provider(self, provider: str) -> list[ModelPublic]:
        """
        Get all models by provider.
        
        Args:
            provider: Provider name
            
        Returns:
            List of ModelPublic instances
        """
        models = self.repository.get_by_provider(provider)
        return [ModelPublic.model_validate(model) for model in models]
    
    def update_model(self, model_id: UUID, model_data: ModelUpdate) -> Optional[ModelPublic]:
        """
        Update a model.
        
        Args:
            model_id: Model UUID
            model_data: Model update data
            
        Returns:
            Updated ModelPublic instance or None if not found
            
        Raises:
            ValueError: If trying to update name to an existing model name
        """
        # If updating name, check it doesn't conflict with existing models
        if model_data.name is not None:
            existing_model = self.repository.get_by_name(model_data.name)
            if existing_model and existing_model.id != model_id:
                raise ValueError(f"Model with name '{model_data.name}' already exists")
        
        model = self.repository.update(model_id, model_data)
        if not model:
            return None
        return ModelPublic.model_validate(model)
    
    def delete_model(self, model_id: UUID) -> bool:
        """
        Delete a model.
        
        Args:
            model_id: Model UUID
            
        Returns:
            True if deleted, False if not found
        """
        return self.repository.delete(model_id)
    
    def toggle_model_enabled(self, model_id: UUID) -> Optional[ModelPublic]:
        """
        Toggle the enabled status of a model.
        
        Args:
            model_id: Model UUID
            
        Returns:
            Updated ModelPublic instance or None if not found
        """
        model = self.repository.toggle_enabled(model_id)
        if not model:
            return None
        return ModelPublic.model_validate(model)
    
    def enable_model(self, model_id: UUID) -> Optional[ModelPublic]:
        """
        Enable a model (set is_enabled to True).
        
        Args:
            model_id: Model UUID
            
        Returns:
            Updated ModelPublic instance or None if not found
        """
        model = self.repository.get_by_id(model_id)
        if not model:
            return None
        
        if model.is_enabled:
            # Already enabled, just return it
            return ModelPublic.model_validate(model)
        
        return self.toggle_model_enabled(model_id)
    
    def disable_model(self, model_id: UUID) -> Optional[ModelPublic]:
        """
        Disable a model (set is_enabled to False).
        
        Args:
            model_id: Model UUID
            
        Returns:
            Updated ModelPublic instance or None if not found
        """
        model = self.repository.get_by_id(model_id)
        if not model:
            return None
        
        if not model.is_enabled:
            # Already disabled, just return it
            return ModelPublic.model_validate(model)
        
        return self.toggle_model_enabled(model_id)
    
    def count_models(self, enabled_only: bool = False) -> int:
        """
        Count total models.
        
        Args:
            enabled_only: If True, only count enabled models
            
        Returns:
            Total count of models
        """
        return self.repository.count(enabled_only=enabled_only)
    
    def get_enabled_models(self, skip: int = 0, limit: int = 100) -> list[ModelPublic]:
        """
        Get all enabled models.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of enabled ModelPublic instances
        """
        return self.get_all_models(skip=skip, limit=limit, enabled_only=True)
    
    def get_available_providers(self) -> list[str]:
        """
        Get a list of unique providers from all models.
        
        Returns:
            List of unique provider names
        """
        models = self.repository.get_all()
        providers = {model.provider for model in models}
        return sorted(list(providers))
