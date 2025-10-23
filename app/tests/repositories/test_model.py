import pytest
from decimal import Decimal
from uuid import uuid4
from sqlmodel import Session

from app.repositories.model import ModelRepository
from app.models import ModelCreate, ModelUpdate


@pytest.fixture(name="repository")
def repository_fixture(session: Session):
    """
    Create a ModelRepository instance with the test session.
    """
    return ModelRepository(session)


@pytest.fixture(name="sample_model_data")
def sample_model_data_fixture():
    """
    Provide sample model creation data.
    """
    return ModelCreate(
        name="GPT-4",
        provider="OpenAI",
        price_per_million_tokens=Decimal("30.000000"),
        is_enabled=True
    )


class TestModelRepositoryCreate:
    """Tests for the create method."""
    
    def test_create_model_success(self, repository: ModelRepository, sample_model_data: ModelCreate):
        """Test creating a new model successfully."""
        model = repository.create(sample_model_data)
        
        assert model.id is not None
        assert model.name == "GPT-4"
        assert model.provider == "OpenAI"
        assert model.price_per_million_tokens == Decimal("30.000000")
        assert model.is_enabled is True
        assert model.created_at is not None
        assert model.updated_at is not None
    
    def test_create_model_with_disabled_status(self, repository: ModelRepository):
        """Test creating a disabled model."""
        model_data = ModelCreate(
            name="Claude-3",
            provider="Anthropic",
            price_per_million_tokens=Decimal("15.000000"),
            is_enabled=False
        )
        
        model = repository.create(model_data)
        
        assert model.is_enabled is False
    
    def test_create_multiple_models(self, repository: ModelRepository):
        """Test creating multiple models."""
        model1_data = ModelCreate(
            name="GPT-4",
            provider="OpenAI",
            price_per_million_tokens=Decimal("30.000000")
        )
        model2_data = ModelCreate(
            name="GPT-3.5",
            provider="OpenAI",
            price_per_million_tokens=Decimal("0.500000")
        )
        
        model1 = repository.create(model1_data)
        model2 = repository.create(model2_data)
        
        assert model1.id != model2.id
        assert model1.name == "GPT-4"
        assert model2.name == "GPT-3.5"


class TestModelRepositoryGetById:
    """Tests for the get_by_id method."""
    
    def test_get_by_id_success(self, repository: ModelRepository, sample_model_data: ModelCreate):
        """Test retrieving a model by ID successfully."""
        created_model = repository.create(sample_model_data)
        
        retrieved_model = repository.get_by_id(created_model.id)
        
        assert retrieved_model is not None
        assert retrieved_model.id == created_model.id
        assert retrieved_model.name == created_model.name
    
    def test_get_by_id_not_found(self, repository: ModelRepository):
        """Test retrieving a non-existent model by ID."""
        non_existent_id = uuid4()
        
        model = repository.get_by_id(non_existent_id)
        
        assert model is None


class TestModelRepositoryGetByName:
    """Tests for the get_by_name method."""
    
    def test_get_by_name_success(self, repository: ModelRepository, sample_model_data: ModelCreate):
        """Test retrieving a model by name successfully."""
        repository.create(sample_model_data)
        
        retrieved_model = repository.get_by_name("GPT-4")
        
        assert retrieved_model is not None
        assert retrieved_model.name == "GPT-4"
        assert retrieved_model.provider == "OpenAI"
    
    def test_get_by_name_not_found(self, repository: ModelRepository):
        """Test retrieving a non-existent model by name."""
        model = repository.get_by_name("NonExistentModel")
        
        assert model is None
    
    def test_get_by_name_case_sensitive(self, repository: ModelRepository, sample_model_data: ModelCreate):
        """Test that name search is case-sensitive."""
        repository.create(sample_model_data)
        
        model = repository.get_by_name("gpt-4")
        
        assert model is None


class TestModelRepositoryGetAll:
    """Tests for the get_all method."""
    
    def test_get_all_empty_database(self, repository: ModelRepository):
        """Test retrieving all models from an empty database."""
        models = repository.get_all()
        
        assert models == []
    
    def test_get_all_with_models(self, repository: ModelRepository):
        """Test retrieving all models."""
        model1_data = ModelCreate(
            name="GPT-4",
            provider="OpenAI",
            price_per_million_tokens=Decimal("30.000000")
        )
        model2_data = ModelCreate(
            name="Claude-3",
            provider="Anthropic",
            price_per_million_tokens=Decimal("15.000000")
        )
        
        repository.create(model1_data)
        repository.create(model2_data)
        
        models = repository.get_all()
        
        assert len(models) == 2
    
    def test_get_all_with_pagination(self, repository: ModelRepository):
        """Test pagination with skip and limit."""
        for i in range(5):
            model_data = ModelCreate(
                name=f"Model-{i}",
                provider="TestProvider",
                price_per_million_tokens=Decimal("10.000000")
            )
            repository.create(model_data)
        
        # Test skip
        models = repository.get_all(skip=2)
        assert len(models) == 3
        
        # Test limit
        models = repository.get_all(limit=2)
        assert len(models) == 2
        
        # Test skip and limit together
        models = repository.get_all(skip=1, limit=2)
        assert len(models) == 2
    
    def test_get_all_enabled_only(self, repository: ModelRepository):
        """Test filtering for enabled models only."""
        enabled_model = ModelCreate(
            name="Enabled-Model",
            provider="TestProvider",
            price_per_million_tokens=Decimal("10.000000"),
            is_enabled=True
        )
        disabled_model = ModelCreate(
            name="Disabled-Model",
            provider="TestProvider",
            price_per_million_tokens=Decimal("10.000000"),
            is_enabled=False
        )
        
        repository.create(enabled_model)
        repository.create(disabled_model)
        
        models = repository.get_all(enabled_only=True)
        
        assert len(models) == 1
        assert models[0].name == "Enabled-Model"


class TestModelRepositoryGetByProvider:
    """Tests for the get_by_provider method."""
    
    def test_get_by_provider_success(self, repository: ModelRepository):
        """Test retrieving models by provider."""
        openai_model1 = ModelCreate(
            name="GPT-4",
            provider="OpenAI",
            price_per_million_tokens=Decimal("30.000000")
        )
        openai_model2 = ModelCreate(
            name="GPT-3.5",
            provider="OpenAI",
            price_per_million_tokens=Decimal("0.500000")
        )
        anthropic_model = ModelCreate(
            name="Claude-3",
            provider="Anthropic",
            price_per_million_tokens=Decimal("15.000000")
        )
        
        repository.create(openai_model1)
        repository.create(openai_model2)
        repository.create(anthropic_model)
        
        openai_models = repository.get_by_provider("OpenAI")
        
        assert len(openai_models) == 2
        assert all(model.provider == "OpenAI" for model in openai_models)
    
    def test_get_by_provider_not_found(self, repository: ModelRepository, sample_model_data: ModelCreate):
        """Test retrieving models by a provider that doesn't exist."""
        repository.create(sample_model_data)
        
        models = repository.get_by_provider("NonExistentProvider")
        
        assert models == []


class TestModelRepositoryUpdate:
    """Tests for the update method."""
    
    def test_update_model_success(self, repository: ModelRepository, sample_model_data: ModelCreate):
        """Test updating a model successfully."""
        created_model = repository.create(sample_model_data)
        original_updated_at = created_model.updated_at
        
        update_data = ModelUpdate(
            name="GPT-4-Turbo",
            price_per_million_tokens=Decimal("25.000000")
        )
        
        updated_model = repository.update(created_model.id, update_data)
        
        assert updated_model is not None
        assert updated_model.name == "GPT-4-Turbo"
        assert updated_model.price_per_million_tokens == Decimal("25.000000")
        assert updated_model.provider == "OpenAI"  # Unchanged
        assert updated_model.updated_at > original_updated_at
    
    def test_update_model_not_found(self, repository: ModelRepository):
        """Test updating a non-existent model."""
        non_existent_id = uuid4()
        update_data = ModelUpdate(name="NewName")
        
        result = repository.update(non_existent_id, update_data)
        
        assert result is None
    
    def test_update_partial_fields(self, repository: ModelRepository, sample_model_data: ModelCreate):
        """Test updating only specific fields."""
        created_model = repository.create(sample_model_data)
        
        # Only update is_enabled
        update_data = ModelUpdate(is_enabled=False)
        updated_model = repository.update(created_model.id, update_data)
        
        assert updated_model is not None
        assert updated_model.is_enabled is False
        assert updated_model.name == created_model.name  # Unchanged
        assert updated_model.provider == created_model.provider  # Unchanged
    
    def test_update_with_empty_data(self, repository: ModelRepository, sample_model_data: ModelCreate):
        """Test update with no fields set (should not change anything except updated_at)."""
        created_model = repository.create(sample_model_data)
        original_name = created_model.name
        
        update_data = ModelUpdate()
        updated_model = repository.update(created_model.id, update_data)
        
        assert updated_model is not None
        assert updated_model.name == original_name


class TestModelRepositoryDelete:
    """Tests for the delete method."""
    
    def test_delete_model_success(self, repository: ModelRepository, sample_model_data: ModelCreate):
        """Test deleting a model successfully."""
        created_model = repository.create(sample_model_data)
        
        result = repository.delete(created_model.id)
        
        assert result is True
        
        # Verify it's actually deleted
        deleted_model = repository.get_by_id(created_model.id)
        assert deleted_model is None
    
    def test_delete_model_not_found(self, repository: ModelRepository):
        """Test deleting a non-existent model."""
        non_existent_id = uuid4()
        
        result = repository.delete(non_existent_id)
        
        assert result is False


class TestModelRepositoryToggleEnabled:
    """Tests for the toggle_enabled method."""
    
    def test_toggle_enabled_from_true_to_false(self, repository: ModelRepository):
        """Test toggling enabled status from True to False."""
        model_data = ModelCreate(
            name="Test-Model",
            provider="TestProvider",
            price_per_million_tokens=Decimal("10.000000"),
            is_enabled=True
        )
        created_model = repository.create(model_data)
        
        toggled_model = repository.toggle_enabled(created_model.id)
        
        assert toggled_model is not None
        assert toggled_model.is_enabled is False
    
    def test_toggle_enabled_from_false_to_true(self, repository: ModelRepository):
        """Test toggling enabled status from False to True."""
        model_data = ModelCreate(
            name="Test-Model",
            provider="TestProvider",
            price_per_million_tokens=Decimal("10.000000"),
            is_enabled=False
        )
        created_model = repository.create(model_data)
        
        toggled_model = repository.toggle_enabled(created_model.id)
        
        assert toggled_model is not None
        assert toggled_model.is_enabled is True
    
    def test_toggle_enabled_multiple_times(self, repository: ModelRepository, sample_model_data: ModelCreate):
        """Test toggling enabled status multiple times."""
        created_model = repository.create(sample_model_data)
        original_status = created_model.is_enabled
        
        # First toggle
        toggled_once = repository.toggle_enabled(created_model.id)
        assert toggled_once is not None
        assert toggled_once.is_enabled != original_status
        
        # Second toggle (should return to original)
        toggled_twice = repository.toggle_enabled(created_model.id)
        assert toggled_twice is not None
        assert toggled_twice.is_enabled == original_status
    
    def test_toggle_enabled_not_found(self, repository: ModelRepository):
        """Test toggling enabled status for a non-existent model."""
        non_existent_id = uuid4()
        
        result = repository.toggle_enabled(non_existent_id)
        
        assert result is None
    
    def test_toggle_enabled_updates_timestamp(self, repository: ModelRepository, sample_model_data: ModelCreate):
        """Test that toggling updates the updated_at timestamp."""
        created_model = repository.create(sample_model_data)
        original_updated_at = created_model.updated_at
        
        toggled_model = repository.toggle_enabled(created_model.id)
        
        assert toggled_model is not None
        assert toggled_model.updated_at > original_updated_at


class TestModelRepositoryCount:
    """Tests for the count method."""
    
    def test_count_empty_database(self, repository: ModelRepository):
        """Test counting models in an empty database."""
        count = repository.count()
        
        assert count == 0
    
    def test_count_all_models(self, repository: ModelRepository):
        """Test counting all models."""
        for i in range(3):
            model_data = ModelCreate(
                name=f"Model-{i}",
                provider="TestProvider",
                price_per_million_tokens=Decimal("10.000000")
            )
            repository.create(model_data)
        
        count = repository.count()
        
        assert count == 3
    
    def test_count_enabled_only(self, repository: ModelRepository):
        """Test counting only enabled models."""
        enabled_models = [
            ModelCreate(
                name=f"Enabled-{i}",
                provider="TestProvider",
                price_per_million_tokens=Decimal("10.000000"),
                is_enabled=True
            ) for i in range(3)
        ]
        disabled_models = [
            ModelCreate(
                name=f"Disabled-{i}",
                provider="TestProvider",
                price_per_million_tokens=Decimal("10.000000"),
                is_enabled=False
            ) for i in range(2)
        ]
        
        for model_data in enabled_models + disabled_models:
            repository.create(model_data)
        
        enabled_count = repository.count(enabled_only=True)
        total_count = repository.count()
        
        assert enabled_count == 3
        assert total_count == 5


class TestModelRepositoryIntegration:
    """Integration tests combining multiple repository operations."""
    
    def test_full_crud_cycle(self, repository: ModelRepository):
        """Test a complete CRUD cycle."""
        # Create
        model_data = ModelCreate(
            name="Test-Model",
            provider="TestProvider",
            price_per_million_tokens=Decimal("10.000000")
        )
        created_model = repository.create(model_data)
        assert created_model.id is not None
        
        # Read
        retrieved_model = repository.get_by_id(created_model.id)
        assert retrieved_model is not None
        assert retrieved_model.name == "Test-Model"
        
        # Update
        update_data = ModelUpdate(name="Updated-Model")
        updated_model = repository.update(created_model.id, update_data)
        assert updated_model is not None
        assert updated_model.name == "Updated-Model"
        
        # Delete
        delete_result = repository.delete(created_model.id)
        assert delete_result is True
        
        # Verify deletion
        deleted_model = repository.get_by_id(created_model.id)
        assert deleted_model is None
    
    def test_complex_query_scenario(self, repository: ModelRepository):
        """Test a complex scenario with multiple queries."""
        # Create multiple models
        models_data = [
            ModelCreate(name="GPT-4", provider="OpenAI", price_per_million_tokens=Decimal("30.0"), is_enabled=True),
            ModelCreate(name="GPT-3.5", provider="OpenAI", price_per_million_tokens=Decimal("0.5"), is_enabled=True),
            ModelCreate(name="Claude-3", provider="Anthropic", price_per_million_tokens=Decimal("15.0"), is_enabled=False),
            ModelCreate(name="Gemini", provider="Google", price_per_million_tokens=Decimal("1.0"), is_enabled=True),
        ]
        
        for model_data in models_data:
            repository.create(model_data)
        
        # Query by provider
        openai_models = repository.get_by_provider("OpenAI")
        assert len(openai_models) == 2
        
        # Count enabled models
        enabled_count = repository.count(enabled_only=True)
        assert enabled_count == 3
        
        # Get all with pagination
        first_page = repository.get_all(limit=2)
        assert len(first_page) == 2
        
        # Toggle one model
        claude = repository.get_by_name("Claude-3")
        assert claude is not None
        toggled = repository.toggle_enabled(claude.id)
        assert toggled is not None
        assert toggled.is_enabled is True
        
        # Verify count increased
        new_enabled_count = repository.count(enabled_only=True)
        assert new_enabled_count == 4
