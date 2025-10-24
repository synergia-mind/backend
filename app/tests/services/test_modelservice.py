import pytest
from decimal import Decimal
from uuid import uuid4
from sqlmodel import Session

from app.services.model import ModelService
from app.models import ModelCreate, ModelUpdate


@pytest.fixture
def model_service(session: Session):
    """Create a ModelService instance with test session."""
    return ModelService(session)


@pytest.fixture
def sample_model_data():
    """Sample model creation data."""
    return ModelCreate(
        name="gpt-4",
        provider="openai",
        price_per_million_tokens=Decimal("30.00"),
        is_enabled=True
    )


@pytest.fixture
def another_model_data():
    """Another sample model creation data."""
    return ModelCreate(
        name="claude-3",
        provider="anthropic",
        price_per_million_tokens=Decimal("15.00"),
        is_enabled=True
    )


class TestCreateModel:
    """Tests for create_model method."""
    
    def test_create_model_success(self, model_service: ModelService, sample_model_data: ModelCreate):
        """Test successful model creation."""
        result = model_service.create_model(sample_model_data)
        
        assert result.name == sample_model_data.name
        assert result.provider == sample_model_data.provider
        assert result.price_per_million_tokens == sample_model_data.price_per_million_tokens
        assert result.is_enabled == sample_model_data.is_enabled
        assert result.id is not None
        assert result.created_at is not None
        assert result.updated_at is not None
    
    def test_create_model_duplicate_name(self, model_service: ModelService, sample_model_data: ModelCreate):
        """Test creating a model with duplicate name raises ValueError."""
        # Create first model
        model_service.create_model(sample_model_data)
        
        # Try to create second model with same name
        with pytest.raises(ValueError, match="Model with name 'gpt-4' already exists"):
            model_service.create_model(sample_model_data)
    
    def test_create_disabled_model(self, model_service: ModelService):
        """Test creating a disabled model."""
        model_data = ModelCreate(
            name="disabled-model",
            provider="test",
            price_per_million_tokens=Decimal("10.00"),
            is_enabled=False
        )
        result = model_service.create_model(model_data)
        
        assert result.is_enabled is False


class TestGetModelById:
    """Tests for get_model_by_id method."""
    
    def test_get_model_by_id_success(self, model_service: ModelService, sample_model_data: ModelCreate):
        """Test successful retrieval by ID."""
        created = model_service.create_model(sample_model_data)
        
        result = model_service.get_model_by_id(created.id)
        
        assert result is not None
        assert result.id == created.id
        assert result.name == created.name
    
    def test_get_model_by_id_not_found(self, model_service: ModelService):
        """Test retrieval with non-existent ID returns None."""
        result = model_service.get_model_by_id(uuid4())
        
        assert result is None


class TestGetModelByName:
    """Tests for get_model_by_name method."""
    
    def test_get_model_by_name_success(self, model_service: ModelService, sample_model_data: ModelCreate):
        """Test successful retrieval by name."""
        created = model_service.create_model(sample_model_data)
        
        result = model_service.get_model_by_name(created.name)
        
        assert result is not None
        assert result.name == created.name
        assert result.id == created.id
    
    def test_get_model_by_name_not_found(self, model_service: ModelService):
        """Test retrieval with non-existent name returns None."""
        result = model_service.get_model_by_name("non-existent-model")
        
        assert result is None


class TestGetAllModels:
    """Tests for get_all_models method."""
    
    def test_get_all_models_empty(self, model_service: ModelService):
        """Test getting all models when none exist."""
        result = model_service.get_all_models()
        
        assert result == []
    
    def test_get_all_models_success(
        self, 
        model_service: ModelService, 
        sample_model_data: ModelCreate,
        another_model_data: ModelCreate
    ):
        """Test getting all models."""
        model_service.create_model(sample_model_data)
        model_service.create_model(another_model_data)
        
        result = model_service.get_all_models()
        
        assert len(result) == 2
        assert {m.name for m in result} == {"gpt-4", "claude-3"}
    
    def test_get_all_models_with_pagination(
        self, 
        model_service: ModelService,
        sample_model_data: ModelCreate,
        another_model_data: ModelCreate
    ):
        """Test getting all models with pagination."""
        model_service.create_model(sample_model_data)
        model_service.create_model(another_model_data)
        
        # Get first page
        result = model_service.get_all_models(skip=0, limit=1)
        assert len(result) == 1
        
        # Get second page
        result = model_service.get_all_models(skip=1, limit=1)
        assert len(result) == 1
    
    def test_get_all_models_enabled_only(self, model_service: ModelService):
        """Test getting only enabled models."""
        # Create enabled model
        enabled_model = ModelCreate(
            name="enabled-model",
            provider="test",
            price_per_million_tokens=Decimal("10.00"),
            is_enabled=True
        )
        model_service.create_model(enabled_model)
        
        # Create disabled model
        disabled_model = ModelCreate(
            name="disabled-model",
            provider="test",
            price_per_million_tokens=Decimal("10.00"),
            is_enabled=False
        )
        model_service.create_model(disabled_model)
        
        result = model_service.get_all_models(enabled_only=True)
        
        assert len(result) == 1
        assert result[0].name == "enabled-model"
        assert result[0].is_enabled is True


class TestGetModelsByProvider:
    """Tests for get_models_by_provider method."""
    
    def test_get_models_by_provider_success(
        self,
        model_service: ModelService,
        sample_model_data: ModelCreate,
        another_model_data: ModelCreate
    ):
        """Test getting models by provider."""
        model_service.create_model(sample_model_data)
        model_service.create_model(another_model_data)
        
        result = model_service.get_models_by_provider("openai")
        
        assert len(result) == 1
        assert result[0].provider == "openai"
    
    def test_get_models_by_provider_not_found(self, model_service: ModelService):
        """Test getting models with non-existent provider."""
        result = model_service.get_models_by_provider("non-existent")
        
        assert result == []


class TestUpdateModel:
    """Tests for update_model method."""
    
    def test_update_model_success(self, model_service: ModelService, sample_model_data: ModelCreate):
        """Test successful model update."""
        created = model_service.create_model(sample_model_data)
        
        update_data = ModelUpdate(
            name="gpt-4-turbo",
            price_per_million_tokens=Decimal("35.00")
        )
        result = model_service.update_model(created.id, update_data)
        
        assert result is not None
        assert result.name == "gpt-4-turbo"
        assert result.price_per_million_tokens == Decimal("35.00")
        assert result.provider == sample_model_data.provider  # Unchanged
    
    def test_update_model_not_found(self, model_service: ModelService):
        """Test updating non-existent model returns None."""
        update_data = ModelUpdate(name="new-name")
        result = model_service.update_model(uuid4(), update_data)
        
        assert result is None
    
    def test_update_model_duplicate_name(
        self,
        model_service: ModelService,
        sample_model_data: ModelCreate,
        another_model_data: ModelCreate
    ):
        """Test updating to duplicate name raises ValueError."""
        model1 = model_service.create_model(sample_model_data)
        model2 = model_service.create_model(another_model_data)
        
        # Try to update model2 name to model1's name
        update_data = ModelUpdate(name=model1.name)
        with pytest.raises(ValueError, match="Model with name 'gpt-4' already exists"):
            model_service.update_model(model2.id, update_data)
    
    def test_update_model_same_name(self, model_service: ModelService, sample_model_data: ModelCreate):
        """Test updating model with its own name is allowed."""
        created = model_service.create_model(sample_model_data)
        
        update_data = ModelUpdate(
            name=created.name,
            price_per_million_tokens=Decimal("40.00")
        )
        result = model_service.update_model(created.id, update_data)
        
        assert result is not None
        assert result.name == created.name
        assert result.price_per_million_tokens == Decimal("40.00")


class TestDeleteModel:
    """Tests for delete_model method."""
    
    def test_delete_model_success(self, model_service: ModelService, sample_model_data: ModelCreate):
        """Test successful model deletion."""
        created = model_service.create_model(sample_model_data)
        
        result = model_service.delete_model(created.id)
        
        assert result is True
        assert model_service.get_model_by_id(created.id) is None
    
    def test_delete_model_not_found(self, model_service: ModelService):
        """Test deleting non-existent model returns False."""
        result = model_service.delete_model(uuid4())
        
        assert result is False


class TestToggleModelEnabled:
    """Tests for toggle_model_enabled method."""
    
    def test_toggle_model_enabled_to_disabled(self, model_service: ModelService, sample_model_data: ModelCreate):
        """Test toggling enabled model to disabled."""
        created = model_service.create_model(sample_model_data)
        assert created.is_enabled is True
        
        result = model_service.toggle_model_enabled(created.id)
        
        assert result is not None
        assert result.is_enabled is False
    
    def test_toggle_model_disabled_to_enabled(self, model_service: ModelService):
        """Test toggling disabled model to enabled."""
        model_data = ModelCreate(
            name="test-model",
            provider="test",
            price_per_million_tokens=Decimal("10.00"),
            is_enabled=False
        )
        created = model_service.create_model(model_data)
        assert created.is_enabled is False
        
        result = model_service.toggle_model_enabled(created.id)
        
        assert result is not None
        assert result.is_enabled is True
    
    def test_toggle_model_not_found(self, model_service: ModelService):
        """Test toggling non-existent model returns None."""
        result = model_service.toggle_model_enabled(uuid4())
        
        assert result is None


class TestEnableModel:
    """Tests for enable_model method."""
    
    def test_enable_model_success(self, model_service: ModelService):
        """Test enabling a disabled model."""
        model_data = ModelCreate(
            name="test-model",
            provider="test",
            price_per_million_tokens=Decimal("10.00"),
            is_enabled=False
        )
        created = model_service.create_model(model_data)
        
        result = model_service.enable_model(created.id)
        
        assert result is not None
        assert result.is_enabled is True
    
    def test_enable_already_enabled_model(self, model_service: ModelService, sample_model_data: ModelCreate):
        """Test enabling already enabled model."""
        created = model_service.create_model(sample_model_data)
        assert created.is_enabled is True
        
        result = model_service.enable_model(created.id)
        
        assert result is not None
        assert result.is_enabled is True
    
    def test_enable_model_not_found(self, model_service: ModelService):
        """Test enabling non-existent model returns None."""
        result = model_service.enable_model(uuid4())
        
        assert result is None


class TestDisableModel:
    """Tests for disable_model method."""
    
    def test_disable_model_success(self, model_service: ModelService, sample_model_data: ModelCreate):
        """Test disabling an enabled model."""
        created = model_service.create_model(sample_model_data)
        
        result = model_service.disable_model(created.id)
        
        assert result is not None
        assert result.is_enabled is False
    
    def test_disable_already_disabled_model(self, model_service: ModelService):
        """Test disabling already disabled model."""
        model_data = ModelCreate(
            name="test-model",
            provider="test",
            price_per_million_tokens=Decimal("10.00"),
            is_enabled=False
        )
        created = model_service.create_model(model_data)
        
        result = model_service.disable_model(created.id)
        
        assert result is not None
        assert result.is_enabled is False
    
    def test_disable_model_not_found(self, model_service: ModelService):
        """Test disabling non-existent model returns None."""
        result = model_service.disable_model(uuid4())
        
        assert result is None


class TestCountModels:
    """Tests for count_models method."""
    
    def test_count_models_empty(self, model_service: ModelService):
        """Test counting models when none exist."""
        result = model_service.count_models()
        
        assert result == 0
    
    def test_count_all_models(
        self,
        model_service: ModelService,
        sample_model_data: ModelCreate,
        another_model_data: ModelCreate
    ):
        """Test counting all models."""
        model_service.create_model(sample_model_data)
        model_service.create_model(another_model_data)
        
        result = model_service.count_models()
        
        assert result == 2
    
    def test_count_enabled_models_only(self, model_service: ModelService):
        """Test counting only enabled models."""
        # Create enabled model
        enabled_model = ModelCreate(
            name="enabled-model",
            provider="test",
            price_per_million_tokens=Decimal("10.00"),
            is_enabled=True
        )
        model_service.create_model(enabled_model)
        
        # Create disabled model
        disabled_model = ModelCreate(
            name="disabled-model",
            provider="test",
            price_per_million_tokens=Decimal("10.00"),
            is_enabled=False
        )
        model_service.create_model(disabled_model)
        
        result = model_service.count_models(enabled_only=True)
        
        assert result == 1


class TestGetEnabledModels:
    """Tests for get_enabled_models method."""
    
    def test_get_enabled_models_success(self, model_service: ModelService):
        """Test getting only enabled models."""
        # Create enabled models
        for i in range(2):
            model_data = ModelCreate(
                name=f"enabled-model-{i}",
                provider="test",
                price_per_million_tokens=Decimal("10.00"),
                is_enabled=True
            )
            model_service.create_model(model_data)
        
        # Create disabled model
        disabled_model = ModelCreate(
            name="disabled-model",
            provider="test",
            price_per_million_tokens=Decimal("10.00"),
            is_enabled=False
        )
        model_service.create_model(disabled_model)
        
        result = model_service.get_enabled_models()
        
        assert len(result) == 2
        assert all(m.is_enabled for m in result)
    
    def test_get_enabled_models_with_pagination(self, model_service: ModelService):
        """Test getting enabled models with pagination."""
        # Create multiple enabled models
        for i in range(3):
            model_data = ModelCreate(
                name=f"enabled-model-{i}",
                provider="test",
                price_per_million_tokens=Decimal("10.00"),
                is_enabled=True
            )
            model_service.create_model(model_data)
        
        result = model_service.get_enabled_models(skip=0, limit=2)
        
        assert len(result) == 2


class TestGetAvailableProviders:
    """Tests for get_available_providers method."""
    
    def test_get_available_providers_empty(self, model_service: ModelService):
        """Test getting providers when no models exist."""
        result = model_service.get_available_providers()
        
        assert result == []
    
    def test_get_available_providers_success(
        self,
        model_service: ModelService,
        sample_model_data: ModelCreate,
        another_model_data: ModelCreate
    ):
        """Test getting unique providers."""
        model_service.create_model(sample_model_data)
        model_service.create_model(another_model_data)
        
        result = model_service.get_available_providers()
        
        assert len(result) == 2
        assert "openai" in result
        assert "anthropic" in result
        assert result == sorted(result)  # Should be sorted
    
    def test_get_available_providers_deduplicated(self, model_service: ModelService):
        """Test that duplicate providers are deduplicated."""
        # Create multiple models with same provider
        for i in range(3):
            model_data = ModelCreate(
                name=f"model-{i}",
                provider="openai",
                price_per_million_tokens=Decimal("10.00"),
                is_enabled=True
            )
            model_service.create_model(model_data)
        
        result = model_service.get_available_providers()
        
        assert len(result) == 1
        assert result[0] == "openai"
