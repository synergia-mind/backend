import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
from uuid import uuid4

from app.core import settings
from app.models import Chat, Model
from decimal import Decimal


@pytest.fixture(name="sample_model")
def sample_model_fixture(session: Session):
    """
    Create a sample model in the database for chat tests.
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


@pytest.fixture(name="sample_chat")
def sample_chat_fixture(session: Session):
    """
    Create a sample chat in the database.
    """
    chat = Chat(
        user_id="test_user_id",
        title="Test Chat",
        summary="This is a test chat"
    )
    session.add(chat)
    session.commit()
    session.refresh(chat)
    return chat


@pytest.fixture(name="multiple_chats")
def multiple_chats_fixture(session: Session):
    """
    Create multiple sample chats in the database.
    """
    chats = [
        Chat(
            user_id="test_user_id",
            title="Chat 1",
            summary="Summary 1",
            is_deleted=False
        ),
        Chat(
            user_id="test_user_id",
            title="Chat 2",
            summary="Summary 2",
            is_deleted=False
        ),
        Chat(
            user_id="test_user_id",
            title="Chat 3",
            summary="Summary 3",
            is_deleted=True  # Soft deleted
        ),
        Chat(
            user_id="other_user_id",
            title="Other User Chat",
            summary="Not accessible",
            is_deleted=False
        ),
    ]
    for chat in chats:
        session.add(chat)
    session.commit()
    for chat in chats:
        session.refresh(chat)
    return chats


class TestCreateChat:
    """Tests for POST /chats/ endpoint."""
    
    def test_create_chat_success(self, client: TestClient):
        """Test successful chat creation."""
        chat_data = {
            "title": "New Chat",
            "summary": "A new chat summary"
        }
        response = client.post(f"{settings.API_V1_STR}/chats/", json=chat_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "New Chat"
        assert data["summary"] == "A new chat summary"
        assert data["user_id"] == "test_user_id"
        assert data["is_deleted"] is False
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data
    
    def test_create_chat_minimal(self, client: TestClient):
        """Test creating a chat with minimal data."""
        chat_data: dict[str, str] = {}
        response = client.post(f"{settings.API_V1_STR}/chats/", json=chat_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == "test_user_id"
        assert data["is_deleted"] is False
    
    def test_create_chat_with_title_only(self, client: TestClient):
        """Test creating a chat with title only."""
        chat_data = {
            "title": "Title Only Chat"
        }
        response = client.post(f"{settings.API_V1_STR}/chats/", json=chat_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Title Only Chat"
        assert data["summary"] is None


class TestGetUserChats:
    """Tests for GET /chats/ endpoint."""
    
    def test_get_user_chats_empty(self, client: TestClient):
        """Test getting chats when user has none."""
        response = client.get(f"{settings.API_V1_STR}/chats/")
        
        assert response.status_code == 200
        assert response.json() == []
    
    def test_get_user_chats(self, client: TestClient, multiple_chats: list[Chat]):
        """Test getting all user chats (excluding deleted by default)."""
        response = client.get(f"{settings.API_V1_STR}/chats/")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2  # Only non-deleted chats for test_user_id
        assert all(chat["user_id"] == "test_user_id" for chat in data)
        assert all(not chat["is_deleted"] for chat in data)
    
    def test_get_user_chats_include_deleted(self, client: TestClient, multiple_chats: list[Chat]):
        """Test getting all user chats including deleted ones."""
        response = client.get(f"{settings.API_V1_STR}/chats/?include_deleted=true")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3  # All chats for test_user_id
        assert all(chat["user_id"] == "test_user_id" for chat in data)
    
    def test_get_user_chats_pagination(self, client: TestClient, multiple_chats: list[Chat]):
        """Test pagination with skip and limit."""
        response = client.get(f"{settings.API_V1_STR}/chats/?skip=1&limit=1")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
    
    def test_get_user_chats_skip_exceeds_count(self, client: TestClient, multiple_chats: list[Chat]):
        """Test pagination when skip exceeds available records."""
        response = client.get(f"{settings.API_V1_STR}/chats/?skip=100")
        
        assert response.status_code == 200
        assert response.json() == []


class TestGetActiveChats:
    """Tests for GET /chats/active endpoint."""
    
    def test_get_active_chats(self, client: TestClient, multiple_chats: list[Chat]):
        """Test getting only active (non-deleted) chats."""
        response = client.get(f"{settings.API_V1_STR}/chats/active")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2  # Only active chats for test_user_id
        assert all(not chat["is_deleted"] for chat in data)
        assert all(chat["user_id"] == "test_user_id" for chat in data)
    
    def test_get_active_chats_empty(self, client: TestClient):
        """Test getting active chats when none exist."""
        response = client.get(f"{settings.API_V1_STR}/chats/active")
        
        assert response.status_code == 200
        assert response.json() == []
    
    def test_get_active_chats_pagination(self, client: TestClient, multiple_chats: list[Chat]):
        """Test pagination for active chats."""
        response = client.get(f"{settings.API_V1_STR}/chats/active?skip=0&limit=1")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert not data[0]["is_deleted"]


class TestGetDeletedChats:
    """Tests for GET /chats/deleted endpoint."""
    
    def test_get_deleted_chats(self, client: TestClient, multiple_chats: list[Chat]):
        """Test getting only soft-deleted chats."""
        response = client.get(f"{settings.API_V1_STR}/chats/deleted")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1  # Only deleted chat for test_user_id
        assert all(chat["is_deleted"] for chat in data)
        assert all(chat["user_id"] == "test_user_id" for chat in data)
    
    def test_get_deleted_chats_empty(self, client: TestClient):
        """Test getting deleted chats when none exist."""
        response = client.get(f"{settings.API_V1_STR}/chats/deleted")
        
        assert response.status_code == 200
        assert response.json() == []
    
    def test_get_deleted_chats_pagination(self, client: TestClient, multiple_chats: list[Chat]):
        """Test pagination for deleted chats."""
        response = client.get(f"{settings.API_V1_STR}/chats/deleted?skip=0&limit=10")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1


class TestCountUserChats:
    """Tests for GET /chats/count endpoint."""
    
    def test_count_user_chats(self, client: TestClient, multiple_chats: list[Chat]):
        """Test counting user chats with breakdown."""
        response = client.get(f"{settings.API_V1_STR}/chats/count")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3  # All chats for test_user_id
        assert data["active"] == 2  # Non-deleted chats
        assert data["deleted"] == 1  # Deleted chats
    
    def test_count_user_chats_empty(self, client: TestClient):
        """Test counting when user has no chats."""
        response = client.get(f"{settings.API_V1_STR}/chats/count")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["active"] == 0
        assert data["deleted"] == 0


class TestGetChatById:
    """Tests for GET /chats/{chat_id} endpoint."""
    
    def test_get_chat_by_id_success(self, client: TestClient, sample_chat: Chat):
        """Test getting a chat by ID."""
        response = client.get(f"{settings.API_V1_STR}/chats/{sample_chat.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(sample_chat.id)
        assert data["title"] == "Test Chat"
        assert data["user_id"] == "test_user_id"
    
    def test_get_chat_by_id_not_found(self, client: TestClient):
        """Test getting a non-existent chat by ID."""
        fake_id = uuid4()
        response = client.get(f"{settings.API_V1_STR}/chats/{fake_id}")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_get_chat_by_id_different_user(self, client: TestClient, multiple_chats: list[Chat]):
        """Test getting a chat that belongs to a different user."""
        other_user_chat = multiple_chats[3]
        response = client.get(f"{settings.API_V1_STR}/chats/{other_user_chat.id}")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


class TestUpdateChat:
    """Tests for PUT /chats/{chat_id} endpoint."""
    
    def test_update_chat_title_and_summary(self, client: TestClient, sample_chat: Chat):
        """Test updating chat title and summary."""
        update_data = {
            "title": "Updated Title",
            "summary": "Updated Summary"
        }
        response = client.put(f"{settings.API_V1_STR}/chats/{sample_chat.id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["summary"] == "Updated Summary"
        assert data["id"] == str(sample_chat.id)
    
    def test_update_chat_title_only(self, client: TestClient, sample_chat: Chat):
        """Test updating only chat title."""
        update_data = {
            "title": "New Title Only"
        }
        response = client.put(f"{settings.API_V1_STR}/chats/{sample_chat.id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "New Title Only"
        assert data["summary"] == "This is a test chat"  # unchanged
    
    def test_update_chat_summary_only(self, client: TestClient, sample_chat: Chat):
        """Test updating only chat summary."""
        update_data = {
            "summary": "New Summary Only"
        }
        response = client.put(f"{settings.API_V1_STR}/chats/{sample_chat.id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Chat"  # unchanged
        assert data["summary"] == "New Summary Only"
    
    def test_update_chat_not_found(self, client: TestClient):
        """Test updating non-existent chat."""
        fake_id = uuid4()
        update_data = {"title": "Test"}
        response = client.put(f"{settings.API_V1_STR}/chats/{fake_id}", json=update_data)
        
        assert response.status_code == 404


class TestUpdateChatTitle:
    """Tests for PATCH /chats/{chat_id}/title endpoint."""
    
    def test_update_chat_title(self, client: TestClient, sample_chat: Chat):
        """Test updating only the chat title."""
        response = client.patch(
            f"{settings.API_V1_STR}/chats/{sample_chat.id}/title?title=Patched Title"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Patched Title"
        assert data["summary"] == "This is a test chat"  # unchanged
    
    def test_update_chat_title_not_found(self, client: TestClient):
        """Test updating title of non-existent chat."""
        fake_id = uuid4()
        response = client.patch(f"{settings.API_V1_STR}/chats/{fake_id}/title?title=Test")
        
        assert response.status_code == 404


class TestUpdateChatSummary:
    """Tests for PATCH /chats/{chat_id}/summary endpoint."""
    
    def test_update_chat_summary(self, client: TestClient, sample_chat: Chat):
        """Test updating only the chat summary."""
        response = client.patch(
            f"{settings.API_V1_STR}/chats/{sample_chat.id}/summary?summary=Patched Summary"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Chat"  # unchanged
        assert data["summary"] == "Patched Summary"
    
    def test_update_chat_summary_not_found(self, client: TestClient):
        """Test updating summary of non-existent chat."""
        fake_id = uuid4()
        response = client.patch(f"{settings.API_V1_STR}/chats/{fake_id}/summary?summary=Test")
        
        assert response.status_code == 404


class TestDeleteChat:
    """Tests for DELETE /chats/{chat_id} endpoint."""
    
    def test_delete_chat_success(self, client: TestClient, sample_chat: Chat):
        """Test successful soft delete of a chat."""
        response = client.delete(f"{settings.API_V1_STR}/chats/{sample_chat.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "deleted successfully" in data["message"]
        
        # Verify chat is soft deleted
        get_response = client.get(f"{settings.API_V1_STR}/chats/{sample_chat.id}")
        assert get_response.status_code == 404  # Not found by default (exclude deleted)
    
    def test_delete_chat_not_found(self, client: TestClient):
        """Test deleting non-existent chat."""
        fake_id = uuid4()
        response = client.delete(f"{settings.API_V1_STR}/chats/{fake_id}")
        
        assert response.status_code == 404
    
    def test_delete_already_deleted_chat(self, client: TestClient, multiple_chats: list[Chat]):
        """Test soft deleting an already deleted chat."""
        deleted_chat = multiple_chats[2]  # Already deleted
        response = client.delete(f"{settings.API_V1_STR}/chats/{deleted_chat.id}")
        
        assert response.status_code == 404


class TestPermanentlyDeleteChat:
    """Tests for DELETE /chats/{chat_id}/permanent endpoint."""
    
    def test_permanently_delete_chat_success(self, client: TestClient, sample_chat: Chat):
        """Test permanent deletion of a chat."""
        response = client.delete(f"{settings.API_V1_STR}/chats/{sample_chat.id}/permanent")
        
        assert response.status_code == 200
        data = response.json()
        assert "permanently deleted" in data["message"]
        
        # Verify chat is permanently deleted
        get_response = client.get(f"{settings.API_V1_STR}/chats/{sample_chat.id}")
        assert get_response.status_code == 404
    
    def test_permanently_delete_chat_not_found(self, client: TestClient):
        """Test permanently deleting non-existent chat."""
        fake_id = uuid4()
        response = client.delete(f"{settings.API_V1_STR}/chats/{fake_id}/permanent")
        
        assert response.status_code == 404
    
    def test_permanently_delete_soft_deleted_chat(self, client: TestClient, multiple_chats: list[Chat]):
        """Test permanently deleting a soft-deleted chat."""
        deleted_chat = multiple_chats[2]
        response = client.delete(f"{settings.API_V1_STR}/chats/{deleted_chat.id}/permanent")
        
        assert response.status_code == 200


class TestRestoreChat:
    """Tests for POST /chats/{chat_id}/restore endpoint."""
    
    def test_restore_chat_success(self, client: TestClient, multiple_chats: list[Chat]):
        """Test restoring a soft-deleted chat."""
        deleted_chat = multiple_chats[2]
        response = client.post(f"{settings.API_V1_STR}/chats/{deleted_chat.id}/restore")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(deleted_chat.id)
        assert data["is_deleted"] is False
    
    def test_restore_chat_not_found(self, client: TestClient):
        """Test restoring non-existent chat."""
        fake_id = uuid4()
        response = client.post(f"{settings.API_V1_STR}/chats/{fake_id}/restore")
        
        assert response.status_code == 404
    
    def test_restore_active_chat(self, client: TestClient, sample_chat: Chat):
        """Test restoring an already active (non-deleted) chat."""
        response = client.post(f"{settings.API_V1_STR}/chats/{sample_chat.id}/restore")
        
        # Restoring an active chat should fail since it only works on deleted chats
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


class TestBulkDeleteChats:
    """Tests for POST /chats/bulk/delete endpoint."""
    
    def test_bulk_delete_chats_success(self, client: TestClient, multiple_chats: list[Chat]):
        """Test bulk soft delete of multiple chats."""
        chat_ids = [str(multiple_chats[0].id), str(multiple_chats[1].id)]
        request_data = {
            "chat_ids": chat_ids
        }
        response = client.post(f"{settings.API_V1_STR}/chats/bulk/delete", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["successful"] == 2
        assert data["failed"] == 0
        assert data["total"] == 2
    
    def test_bulk_delete_chats_partial_success(self, client: TestClient, multiple_chats: list[Chat]):
        """Test bulk delete with some valid and some invalid chat IDs."""
        fake_id = str(uuid4())
        chat_ids = [str(multiple_chats[0].id), fake_id]
        request_data = {
            "chat_ids": chat_ids
        }
        response = client.post(f"{settings.API_V1_STR}/chats/bulk/delete", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["successful"] == 1
        assert data["failed"] == 1
        assert data["total"] == 2
    
    def test_bulk_delete_chats_empty_list(self, client: TestClient):
        """Test bulk delete with empty list."""
        request_data: dict[str, list[str]] = {
            "chat_ids": []
        }
        response = client.post(f"{settings.API_V1_STR}/chats/bulk/delete", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["successful"] == 0
        assert data["failed"] == 0
        assert data["total"] == 0


class TestBulkRestoreChats:
    """Tests for POST /chats/bulk/restore endpoint."""
    
    def test_bulk_restore_chats_success(self, client: TestClient, multiple_chats: list[Chat]):
        """Test bulk restore of multiple soft-deleted chats."""
        # First delete a chat to have something to restore
        deleted_chat_id = multiple_chats[2].id  # Already deleted (UUID object)
        request_data = {
            "chat_ids": [str(deleted_chat_id)]
        }
        response = client.post(f"{settings.API_V1_STR}/chats/bulk/restore", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["successful"] == 1
        assert data["failed"] == 0
        assert data["total"] == 1
    
    def test_bulk_restore_chats_partial_success(self, client: TestClient, multiple_chats: list[Chat]):
        """Test bulk restore with some valid and some invalid chat IDs."""
        fake_id = str(uuid4())
        deleted_chat_id = str(multiple_chats[2].id)
        chat_ids = [deleted_chat_id, fake_id]
        request_data = {
            "chat_ids": chat_ids
        }
        response = client.post(f"{settings.API_V1_STR}/chats/bulk/restore", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["successful"] == 1
        assert data["failed"] == 1
        assert data["total"] == 2
    
    def test_bulk_restore_chats_empty_list(self, client: TestClient):
        """Test bulk restore with empty list."""
        request_data: dict[str, list[str]] = {
            "chat_ids": []
        }
        response = client.post(f"{settings.API_V1_STR}/chats/bulk/restore", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["successful"] == 0
        assert data["failed"] == 0
        assert data["total"] == 0


class TestBulkPermanentlyDeleteChats:
    """Tests for POST /chats/bulk/delete/permanent endpoint."""
    
    def test_bulk_permanently_delete_chats_success(self, client: TestClient, multiple_chats: list[Chat]):
        """Test bulk permanent delete of multiple chats."""
        chat_ids = [str(multiple_chats[0].id), str(multiple_chats[1].id)]
        request_data = {
            "chat_ids": chat_ids
        }
        response = client.post(f"{settings.API_V1_STR}/chats/bulk/delete/permanent", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["successful"] == 2
        assert data["failed"] == 0
        assert data["total"] == 2
        
        # Verify chats are permanently deleted
        for chat_id in chat_ids:
            get_response = client.get(f"{settings.API_V1_STR}/chats/{chat_id}")
            assert get_response.status_code == 404
    
    def test_bulk_permanently_delete_chats_partial_success(self, client: TestClient, multiple_chats: list[Chat]):
        """Test bulk permanent delete with some valid and some invalid chat IDs."""
        fake_id = str(uuid4())
        chat_ids = [str(multiple_chats[0].id), fake_id]
        request_data = {
            "chat_ids": chat_ids
        }
        response = client.post(f"{settings.API_V1_STR}/chats/bulk/delete/permanent", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["successful"] == 1
        assert data["failed"] == 1
        assert data["total"] == 2
    
    def test_bulk_permanently_delete_chats_empty_list(self, client: TestClient):
        """Test bulk permanent delete with empty list."""
        request_data: dict[str, list[str]] = {
            "chat_ids": []
        }
        response = client.post(f"{settings.API_V1_STR}/chats/bulk/delete/permanent", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["successful"] == 0
        assert data["failed"] == 0
        assert data["total"] == 0


class TestCheckChatExists:
    """Tests for GET /chats/{chat_id}/exists endpoint."""
    
    def test_check_chat_exists_true(self, client: TestClient, sample_chat: Chat):
        """Test checking existence of an existing chat."""
        response = client.get(f"{settings.API_V1_STR}/chats/{sample_chat.id}/exists")
        
        assert response.status_code == 200
        data = response.json()
        assert data["exists"] is True
    
    def test_check_chat_exists_false(self, client: TestClient):
        """Test checking existence of non-existent chat."""
        fake_id = uuid4()
        response = client.get(f"{settings.API_V1_STR}/chats/{fake_id}/exists")
        
        assert response.status_code == 200
        data = response.json()
        assert data["exists"] is False
    
    def test_check_chat_exists_different_user(self, client: TestClient, multiple_chats: list[Chat]):
        """Test checking existence of chat belonging to different user."""
        other_user_chat = multiple_chats[3]
        response = client.get(f"{settings.API_V1_STR}/chats/{other_user_chat.id}/exists")
        
        assert response.status_code == 200
        data = response.json()
        assert data["exists"] is False
