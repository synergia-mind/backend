import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
from decimal import Decimal
from uuid import uuid4

from app.core import settings
from app.models import Model


@pytest.fixture(name="sample_model")
def sample_model_fixture(session: Session):
    """
    Create a sample model in the database.
    """
    model = Model(
        name="gpt-4",
        provider="OpenAI",
        price_per_million_tokens=Decimal("30.000000"),
        is_enabled=True
    )
    session.add(model)
    session.commit()
    session.refresh(model)
    return model


@pytest.fixture(name="multiple_models")
def multiple_models_fixture(session: Session):
    """
    Create multiple sample models in the database.
    """
    models = [
        Model(
            name="gpt-4",
            provider="OpenAI",
            price_per_million_tokens=Decimal("30.000000"),
            is_enabled=True
        ),
        Model(
            name="gpt-3.5-turbo",
            provider="OpenAI",
            price_per_million_tokens=Decimal("0.500000"),
            is_enabled=True
        ),
        Model(
            name="claude-3-opus",
            provider="Anthropic",
            price_per_million_tokens=Decimal("15.000000"),
            is_enabled=True
        ),
        Model(
            name="claude-3-sonnet",
            provider="Anthropic",
            price_per_million_tokens=Decimal("3.000000"),
            is_enabled=False
        ),
    ]
    for model in models:
        session.add(model)
    session.commit()
    for model in models:
        session.refresh(model)
    return models


class TestCreateModel:
    """Tests for POST /models/ endpoint."""
    
    def test_create_model_success(self, client: TestClient):
        """Test successful model creation."""
        model_data = {
            "name": "gpt-4",
            "provider": "OpenAI",
            "price_per_million_tokens": 30.0,
            "is_enabled": True
        }
        response = client.post(f"{settings.API_V1_STR}/models/", json=model_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "gpt-4"
        assert data["provider"] == "OpenAI"
        assert float(data["price_per_million_tokens"]) == 30.0
        assert data["is_enabled"] is True
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data
    
    def test_create_model_duplicate_name(self, client: TestClient, sample_model: Model):
        """Test creating a model with duplicate name fails."""
        model_data = {
            "name": "gpt-4",
            "provider": "OpenAI",
            "price_per_million_tokens": 30.0,
            "is_enabled": True
        }
        response = client.post(f"{settings.API_V1_STR}/models/", json=model_data)
        
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]
    
    def test_create_model_default_enabled(self, client: TestClient):
        """Test model is enabled by default."""
        model_data = {
            "name": "gpt-4",
            "provider": "OpenAI",
            "price_per_million_tokens": 30.0
        }
        response = client.post(f"{settings.API_V1_STR}/models/", json=model_data)
        
        assert response.status_code == 201
        assert response.json()["is_enabled"] is True


class TestGetAllModels:
    """Tests for GET /models/ endpoint."""
    
    def test_get_all_models_empty(self, client: TestClient):
        """Test getting all models when database is empty."""
        response = client.get(f"{settings.API_V1_STR}/models/")
        
        assert response.status_code == 200
        assert response.json() == []
    
    def test_get_all_models(self, client: TestClient, multiple_models: list[Model]):
        """Test getting all models."""
        response = client.get(f"{settings.API_V1_STR}/models/")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 4
        assert all("id" in model for model in data)
        assert all("name" in model for model in data)
    
    def test_get_all_models_pagination(self, client: TestClient, multiple_models: list[Model]):
        """Test pagination with skip and limit."""
        response = client.get(f"{settings.API_V1_STR}/models/?skip=1&limit=2")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
    
    def test_get_all_models_enabled_only(self, client: TestClient, multiple_models: list[Model]):
        """Test filtering for enabled models only."""
        response = client.get(f"{settings.API_V1_STR}/models/?enabled_only=true")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert all(model["is_enabled"] for model in data)


class TestGetEnabledModels:
    """Tests for GET /models/enabled endpoint."""
    
    def test_get_enabled_models(self, client: TestClient, multiple_models: list[Model]):
        """Test getting only enabled models."""
        response = client.get(f"{settings.API_V1_STR}/models/enabled")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert all(model["is_enabled"] for model in data)
    
    def test_get_enabled_models_pagination(self, client: TestClient, multiple_models: list[Model]):
        """Test pagination for enabled models."""
        response = client.get(f"{settings.API_V1_STR}/models/enabled?skip=1&limit=1")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["is_enabled"]


class TestGetAvailableProviders:
    """Tests for GET /models/providers endpoint."""
    
    def test_get_available_providers(self, client: TestClient, multiple_models: list[Model]):
        """Test getting unique providers."""
        response = client.get(f"{settings.API_V1_STR}/models/providers")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert "OpenAI" in data
        assert "Anthropic" in data
    
    def test_get_available_providers_empty(self, client: TestClient):
        """Test getting providers when no models exist."""
        response = client.get(f"{settings.API_V1_STR}/models/providers")
        
        assert response.status_code == 200
        assert response.json() == []


class TestGetModelsByProvider:
    """Tests for GET /models/provider/{provider} endpoint."""
    
    def test_get_models_by_provider_openai(self, client: TestClient, multiple_models: list[Model]):
        """Test getting models by OpenAI provider."""
        response = client.get(f"{settings.API_V1_STR}/models/provider/OpenAI")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all(model["provider"] == "OpenAI" for model in data)
    
    def test_get_models_by_provider_anthropic(self, client: TestClient, multiple_models: list[Model]):
        """Test getting models by Anthropic provider."""
        response = client.get(f"{settings.API_V1_STR}/models/provider/Anthropic")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all(model["provider"] == "Anthropic" for model in data)
    
    def test_get_models_by_provider_nonexistent(self, client: TestClient, multiple_models: list[Model]):
        """Test getting models by non-existent provider."""
        response = client.get(f"{settings.API_V1_STR}/models/provider/Google")
        
        assert response.status_code == 200
        assert response.json() == []


class TestCountModels:
    """Tests for GET /models/count endpoint."""
    
    def test_count_all_models(self, client: TestClient, multiple_models: list[Model]):
        """Test counting all models."""
        response = client.get(f"{settings.API_V1_STR}/models/count")
        
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 4
    
    def test_count_enabled_models(self, client: TestClient, multiple_models: list[Model]):
        """Test counting enabled models only."""
        response = client.get(f"{settings.API_V1_STR}/models/count?enabled_only=true")
        
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 3
    
    def test_count_models_empty(self, client: TestClient):
        """Test counting models when database is empty."""
        response = client.get(f"{settings.API_V1_STR}/models/count")
        
        assert response.status_code == 200
        assert response.json()["count"] == 0


class TestGetModelByName:
    """Tests for GET /models/name/{name} endpoint."""
    
    def test_get_model_by_name_success(self, client: TestClient, sample_model: Model):
        """Test getting a model by name."""
        response = client.get(f"{settings.API_V1_STR}/models/name/gpt-4")
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "gpt-4"
        assert data["id"] == str(sample_model.id)
    
    def test_get_model_by_name_not_found(self, client: TestClient):
        """Test getting a non-existent model by name."""
        response = client.get(f"{settings.API_V1_STR}/models/name/nonexistent")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


class TestGetModelById:
    """Tests for GET /models/{model_id} endpoint."""
    
    def test_get_model_by_id_success(self, client: TestClient, sample_model: Model):
        """Test getting a model by ID."""
        response = client.get(f"{settings.API_V1_STR}/models/{sample_model.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(sample_model.id)
        assert data["name"] == "gpt-4"
    
    def test_get_model_by_id_not_found(self, client: TestClient):
        """Test getting a non-existent model by ID."""
        fake_id = uuid4()
        response = client.get(f"{settings.API_V1_STR}/models/{fake_id}")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


class TestUpdateModel:
    """Tests for PUT /models/{model_id} endpoint."""
    
    def test_update_model_name(self, client: TestClient, sample_model: Model):
        """Test updating model name."""
        update_data = {
            "name": "gpt-4-turbo",
            "provider": "OpenAI",
            "price_per_million_tokens": 35.0,
            "is_enabled": True
        }
        response = client.put(f"{settings.API_V1_STR}/models/{sample_model.id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "gpt-4-turbo"
        assert float(data["price_per_million_tokens"]) == 35.0
    
    def test_update_model_partial(self, client: TestClient, sample_model: Model):
        """Test partial update of model."""
        update_data = {
            "price_per_million_tokens": 25.0
        }
        response = client.put(f"{settings.API_V1_STR}/models/{sample_model.id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "gpt-4"  # unchanged
        assert float(data["price_per_million_tokens"]) == 25.0
    
    def test_update_model_duplicate_name(self, client: TestClient, multiple_models: list[Model]):
        """Test updating model to duplicate name fails."""
        update_data = {
            "name": "gpt-3.5-turbo"  # already exists
        }
        response = client.put(f"{settings.API_V1_STR}/models/{multiple_models[0].id}", json=update_data)
        
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]
    
    def test_update_model_not_found(self, client: TestClient):
        """Test updating non-existent model."""
        fake_id = uuid4()
        update_data = {"name": "test"}
        response = client.put(f"{settings.API_V1_STR}/models/{fake_id}", json=update_data)
        
        assert response.status_code == 404


class TestToggleModelEnabled:
    """Tests for PATCH /models/{model_id}/toggle endpoint."""
    
    def test_toggle_model_enabled_to_disabled(self, client: TestClient, sample_model: Model):
        """Test toggling enabled model to disabled."""
        response = client.patch(f"{settings.API_V1_STR}/models/{sample_model.id}/toggle")
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_enabled"] is False
    
    def test_toggle_model_disabled_to_enabled(self, client: TestClient, multiple_models: list[Model]):
        """Test toggling disabled model to enabled."""
        disabled_model = multiple_models[3]  # claude-3-sonnet is disabled
        response = client.patch(f"{settings.API_V1_STR}/models/{disabled_model.id}/toggle")
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_enabled"] is True
    
    def test_toggle_model_not_found(self, client: TestClient):
        """Test toggling non-existent model."""
        fake_id = uuid4()
        response = client.patch(f"{settings.API_V1_STR}/models/{fake_id}/toggle")
        
        assert response.status_code == 404


class TestEnableModel:
    """Tests for PATCH /models/{model_id}/enable endpoint."""
    
    def test_enable_disabled_model(self, client: TestClient, multiple_models: list[Model]):
        """Test enabling a disabled model."""
        disabled_model = multiple_models[3]
        response = client.patch(f"{settings.API_V1_STR}/models/{disabled_model.id}/enable")
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_enabled"] is True
    
    def test_enable_already_enabled_model(self, client: TestClient, sample_model: Model):
        """Test enabling an already enabled model."""
        response = client.patch(f"{settings.API_V1_STR}/models/{sample_model.id}/enable")
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_enabled"] is True
    
    def test_enable_model_not_found(self, client: TestClient):
        """Test enabling non-existent model."""
        fake_id = uuid4()
        response = client.patch(f"{settings.API_V1_STR}/models/{fake_id}/enable")
        
        assert response.status_code == 404


class TestDisableModel:
    """Tests for PATCH /models/{model_id}/disable endpoint."""
    
    def test_disable_enabled_model(self, client: TestClient, sample_model: Model):
        """Test disabling an enabled model."""
        response = client.patch(f"{settings.API_V1_STR}/models/{sample_model.id}/disable")
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_enabled"] is False
    
    def test_disable_already_disabled_model(self, client: TestClient, multiple_models: list[Model]):
        """Test disabling an already disabled model."""
        disabled_model = multiple_models[3]
        response = client.patch(f"{settings.API_V1_STR}/models/{disabled_model.id}/disable")
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_enabled"] is False
    
    def test_disable_model_not_found(self, client: TestClient):
        """Test disabling non-existent model."""
        fake_id = uuid4()
        response = client.patch(f"{settings.API_V1_STR}/models/{fake_id}/disable")
        
        assert response.status_code == 404


class TestDeleteModel:
    """Tests for DELETE /models/{model_id} endpoint."""
    
    def test_delete_model_success(self, client: TestClient, sample_model: Model):
        """Test successful model deletion."""
        response = client.delete(f"{settings.API_V1_STR}/models/{sample_model.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "deleted successfully" in data["message"]
        
        # Verify model is deleted
        get_response = client.get(f"{settings.API_V1_STR}/models/{sample_model.id}")
        assert get_response.status_code == 404
    
    def test_delete_model_not_found(self, client: TestClient):
        """Test deleting non-existent model."""
        fake_id = uuid4()
        response = client.delete(f"{settings.API_V1_STR}/models/{fake_id}")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
