from typing import Optional
from uuid import UUID
from sqlmodel import Session, select
from app.models import Model, ModelCreate, ModelUpdate
from datetime import datetime, timezone


class ModelRepository:
    """Repository for Model CRUD operations."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create(self, model_data: ModelCreate) -> Model:
        """
        Create a new model.
        
        Args:
            model_data: Model creation data
            
        Returns:
            Created model instance
        """
        model = Model.model_validate(model_data)
        self.session.add(model)
        self.session.commit()
        self.session.refresh(model)
        return model
    
    def get_by_id(self, model_id: UUID) -> Optional[Model]:
        """
        Get a model by ID.
        
        Args:
            model_id: Model UUID
            
        Returns:
            Model instance or None if not found
        """
        statement = select(Model).where(Model.id == model_id)
        return self.session.exec(statement).first()
    
    def get_by_name(self, name: str) -> Optional[Model]:
        """
        Get a model by name.
        
        Args:
            name: Model name
            
        Returns:
            Model instance or None if not found
        """
        statement = select(Model).where(Model.name == name)
        return self.session.exec(statement).first()
    
    def get_all(
        self, 
        skip: int = 0, 
        limit: int = 100,
        enabled_only: bool = False
    ) -> list[Model]:
        """
        Get all models with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            enabled_only: If True, only return enabled models
            
        Returns:
            List of model instances
        """
        statement = select(Model)
        
        if enabled_only:
            statement = statement.where(Model.is_enabled == True)
        
        statement = statement.offset(skip).limit(limit)
        return list(self.session.exec(statement).all())
    
    def get_by_provider(self, provider: str) -> list[Model]:
        """
        Get all models by provider.
        
        Args:
            provider: Provider name
            
        Returns:
            List of model instances
        """
        statement = select(Model).where(Model.provider == provider)
        return list(self.session.exec(statement).all())
    
    def update(self, model_id: UUID, model_data: ModelUpdate) -> Optional[Model]:
        """
        Update a model.
        
        Args:
            model_id: Model UUID
            model_data: Model update data
            
        Returns:
            Updated model instance or None if not found
        """
        model = self.get_by_id(model_id)
        if not model:
            return None
        
        update_data = model_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(model, key, value)
        
        model.updated_at = datetime.now(timezone.utc)
        self.session.add(model)
        self.session.commit()
        self.session.refresh(model)
        return model
    
    def delete(self, model_id: UUID) -> bool:
        """
        Delete a model (hard delete).
        
        Args:
            model_id: Model UUID
            
        Returns:
            True if deleted, False if not found
        """
        model = self.get_by_id(model_id)
        if not model:
            return False
        
        self.session.delete(model)
        self.session.commit()
        return True
    
    def toggle_enabled(self, model_id: UUID) -> Optional[Model]:
        """
        Toggle the enabled status of a model.
        
        Args:
            model_id: Model UUID
            
        Returns:
            Updated model instance or None if not found
        """
        model = self.get_by_id(model_id)
        if not model:
            return None
        
        model.is_enabled = not model.is_enabled
        model.updated_at = datetime.now(timezone.utc)
        self.session.add(model)
        self.session.commit()
        self.session.refresh(model)
        return model
    
    def count(self, enabled_only: bool = False) -> int:
        """
        Count total models.
        
        Args:
            enabled_only: If True, only count enabled models
            
        Returns:
            Total count of models
        """
        statement = select(Model)
        
        if enabled_only:
            statement = statement.where(Model.is_enabled == True)
        
        results = self.session.exec(statement).all()
        return len(list(results))
