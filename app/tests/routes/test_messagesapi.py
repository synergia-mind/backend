import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
from uuid import uuid4
from decimal import Decimal

from app.core import settings
from app.models import Chat, Model, Message, MessageType


@pytest.fixture(name="sample_model")
def sample_model_fixture(session: Session):
    """Create a sample model in the database for message tests."""
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


@pytest.fixture(name="disabled_model")
def disabled_model_fixture(session: Session):
    """Create a disabled model in the database."""
    model = Model(
        name="gpt-3.5-turbo",
        provider="OpenAI",
        price_per_million_tokens=Decimal("1.500000"),
        is_enabled=False
    )
    session.add(model)
    session.commit()
    session.refresh(model)
    return model


@pytest.fixture(name="sample_chat")
def sample_chat_fixture(session: Session):
    """Create a sample chat in the database."""
    chat = Chat(
        user_id="test_user_id",
        title="Test Chat",
        summary="This is a test chat"
    )
    session.add(chat)
    session.commit()
    session.refresh(chat)
    return chat


@pytest.fixture(name="other_user_chat")
def other_user_chat_fixture(session: Session):
    """Create a chat belonging to a different user."""
    chat = Chat(
        user_id="other_user_id",
        title="Other User Chat",
        summary="Not accessible"
    )
    session.add(chat)
    session.commit()
    session.refresh(chat)
    return chat


@pytest.fixture(name="sample_message")
def sample_message_fixture(session: Session, sample_chat: Chat, sample_model: Model):
    """Create a sample message in the database."""
    message = Message(
        chat_id=sample_chat.id,
        model_id=sample_model.id,
        type=MessageType.user,
        content="Hello, this is a test message",
        tokens=10
    )
    session.add(message)
    session.commit()
    session.refresh(message)
    return message


@pytest.fixture(name="multiple_messages")
def multiple_messages_fixture(session: Session, sample_chat: Chat, sample_model: Model):
    """Create multiple sample messages in the database."""
    messages = [
        Message(
            chat_id=sample_chat.id,
            model_id=sample_model.id,
            type=MessageType.user,
            content="User message 1",
            tokens=5,
            is_deleted=False
        ),
        Message(
            chat_id=sample_chat.id,
            model_id=sample_model.id,
            type=MessageType.assistant,
            content="AI response 1",
            tokens=15,
            is_deleted=False
        ),
        Message(
            chat_id=sample_chat.id,
            model_id=sample_model.id,
            type=MessageType.user,
            content="User message 2",
            tokens=7,
            is_deleted=False
        ),
        Message(
            chat_id=sample_chat.id,
            model_id=sample_model.id,
            type=MessageType.assistant,
            content="AI response 2",
            tokens=20,
            is_deleted=False
        ),
        Message(
            chat_id=sample_chat.id,
            model_id=sample_model.id,
            type=MessageType.user,
            content="Deleted message",
            tokens=3,
            is_deleted=True
        ),
    ]
    for message in messages:
        session.add(message)
    session.commit()
    for message in messages:
        session.refresh(message)
    return messages


class TestCreateMessage:
    """Tests for POST /messages/ endpoint."""
    
    def test_create_message_success(self, client: TestClient, sample_chat: Chat, sample_model: Model):
        """Test successful message creation."""
        message_data = {
            "chat_id": str(sample_chat.id),
            "model_id": str(sample_model.id),
            "type": "user",
            "content": "New test message",
            "tokens": 10
        }
        response = client.post(f"{settings.API_V1_STR}/messages/", json=message_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["content"] == "New test message"
        assert data["type"] == "user"
        assert data["tokens"] == 10
        assert data["chat_id"] == str(sample_chat.id)
        assert data["model_id"] == str(sample_model.id)
        assert "id" in data
        assert "created_at" in data
        assert "model" in data
        assert data["model"]["name"] == "gpt-4"
    
    def test_create_message_without_tokens(self, client: TestClient, sample_chat: Chat, sample_model: Model):
        """Test creating a message without tokens."""
        message_data = {
            "chat_id": str(sample_chat.id),
            "model_id": str(sample_model.id),
            "type": "ai",
            "content": "AI response without token count"
        }
        response = client.post(f"{settings.API_V1_STR}/messages/", json=message_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["content"] == "AI response without token count"
        assert data["tokens"] is None
    
    def test_create_message_chat_not_found(self, client: TestClient, sample_model: Model):
        """Test creating a message with non-existent chat."""
        fake_chat_id = uuid4()
        message_data = {
            "chat_id": str(fake_chat_id),
            "model_id": str(sample_model.id),
            "type": "user",
            "content": "Test"
        }
        response = client.post(f"{settings.API_V1_STR}/messages/", json=message_data)
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_create_message_model_not_found(self, client: TestClient, sample_chat: Chat):
        """Test creating a message with non-existent model."""
        fake_model_id = uuid4()
        message_data = {
            "chat_id": str(sample_chat.id),
            "model_id": str(fake_model_id),
            "type": "user",
            "content": "Test"
        }
        response = client.post(f"{settings.API_V1_STR}/messages/", json=message_data)
        
        assert response.status_code == 400
        assert "does not exist" in response.json()["detail"]
    
    def test_create_message_disabled_model(self, client: TestClient, sample_chat: Chat, disabled_model: Model):
        """Test creating a message with a disabled model."""
        message_data = {
            "chat_id": str(sample_chat.id),
            "model_id": str(disabled_model.id),
            "type": "user",
            "content": "Test"
        }
        response = client.post(f"{settings.API_V1_STR}/messages/", json=message_data)
        
        assert response.status_code == 400
        assert "disabled" in response.json()["detail"]
    
    def test_create_message_other_user_chat(self, client: TestClient, other_user_chat: Chat, sample_model: Model):
        """Test creating a message in another user's chat."""
        message_data = {
            "chat_id": str(other_user_chat.id),
            "model_id": str(sample_model.id),
            "type": "user",
            "content": "Test"
        }
        response = client.post(f"{settings.API_V1_STR}/messages/", json=message_data)
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


class TestCreateMessageWithAutoChat:
    """Tests for POST /messages/with-chat endpoint."""
    
    def test_create_message_with_auto_chat_success(self, client: TestClient, sample_model: Model):
        """Test creating a message with automatic chat creation."""
        request_data = {
            "model_id": str(sample_model.id),
            "content": "This is a test message that will create a new chat",
            "message_type": "user",
            "tokens": 12,
            "chat_title": "Auto Created Chat"
        }
        response = client.post(f"{settings.API_V1_STR}/messages/with-chat", json=request_data)
        
        assert response.status_code == 201
        data = response.json()
        assert "message" in data
        assert "chat_id" in data
        assert data["message"]["content"] == "This is a test message that will create a new chat"
        assert data["message"]["type"] == "user"
        assert data["message"]["tokens"] == 12
        
        # Verify chat was created
        chat_response = client.get(f"{settings.API_V1_STR}/chats/{data['chat_id']}")
        assert chat_response.status_code == 200
        chat_data = chat_response.json()
        assert chat_data["title"] == "Auto Created Chat"
    
    def test_create_message_with_auto_chat_default_title(self, client: TestClient, sample_model: Model):
        """Test creating a message with auto chat using default title."""
        request_data = {
            "model_id": str(sample_model.id),
            "content": "Short message",
            "message_type": "user"
        }
        response = client.post(f"{settings.API_V1_STR}/messages/with-chat", json=request_data)
        
        assert response.status_code == 201
        data = response.json()
        assert "chat_id" in data
        
        # Verify chat has default title from content
        chat_response = client.get(f"{settings.API_V1_STR}/chats/{data['chat_id']}")
        assert chat_response.status_code == 200
        chat_data = chat_response.json()
        assert chat_data["title"] == "Short message"
    
    def test_create_message_with_auto_chat_long_content(self, client: TestClient, sample_model: Model):
        """Test creating a message with auto chat and long content (title truncation)."""
        long_content = "A" * 100
        request_data = {
            "model_id": str(sample_model.id),
            "content": long_content,
            "message_type": "user"
        }
        response = client.post(f"{settings.API_V1_STR}/messages/with-chat", json=request_data)
        
        assert response.status_code == 201
        data = response.json()
        
        # Verify chat title is truncated
        chat_response = client.get(f"{settings.API_V1_STR}/chats/{data['chat_id']}")
        assert chat_response.status_code == 200
        chat_data = chat_response.json()
        assert len(chat_data["title"]) <= 53  # 50 chars + "..."
    
    def test_create_message_with_auto_chat_invalid_model(self, client: TestClient):
        """Test creating a message with auto chat using invalid model."""
        fake_model_id = uuid4()
        request_data = {
            "model_id": str(fake_model_id),
            "content": "Test",
            "message_type": "user"
        }
        response = client.post(f"{settings.API_V1_STR}/messages/with-chat", json=request_data)
        
        assert response.status_code == 400
        assert "does not exist" in response.json()["detail"]


class TestGetChatMessages:
    """Tests for GET /messages/chat/{chat_id} endpoint."""
    
    def test_get_chat_messages_success(self, client: TestClient, sample_chat: Chat, multiple_messages: list[Message]):
        """Test getting all messages for a chat."""
        response = client.get(f"{settings.API_V1_STR}/messages/chat/{sample_chat.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 4  # Excludes deleted message by default
        assert all(msg["chat_id"] == str(sample_chat.id) for msg in data)
    
    def test_get_chat_messages_include_deleted(self, client: TestClient, sample_chat: Chat, multiple_messages: list[Message]):
        """Test getting all messages including deleted ones."""
        response = client.get(f"{settings.API_V1_STR}/messages/chat/{sample_chat.id}?include_deleted=true")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5  # Includes deleted message
    
    def test_get_chat_messages_pagination(self, client: TestClient, sample_chat: Chat, multiple_messages: list[Message]):
        """Test pagination of chat messages."""
        response = client.get(f"{settings.API_V1_STR}/messages/chat/{sample_chat.id}?skip=1&limit=2")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
    
    def test_get_chat_messages_empty(self, client: TestClient, sample_chat: Chat):
        """Test getting messages from a chat with no messages."""
        response = client.get(f"{settings.API_V1_STR}/messages/chat/{sample_chat.id}")
        
        assert response.status_code == 200
        assert response.json() == []
    
    def test_get_chat_messages_chat_not_found(self, client: TestClient):
        """Test getting messages from non-existent chat."""
        fake_chat_id = uuid4()
        response = client.get(f"{settings.API_V1_STR}/messages/chat/{fake_chat_id}")
        
        assert response.status_code == 404
    
    def test_get_chat_messages_other_user_chat(self, client: TestClient, other_user_chat: Chat):
        """Test getting messages from another user's chat."""
        response = client.get(f"{settings.API_V1_STR}/messages/chat/{other_user_chat.id}")
        
        assert response.status_code == 404


class TestGetActiveMessages:
    """Tests for GET /messages/chat/{chat_id}/active endpoint."""
    
    def test_get_active_messages(self, client: TestClient, sample_chat: Chat, multiple_messages: list[Message]):
        """Test getting only active messages."""
        response = client.get(f"{settings.API_V1_STR}/messages/chat/{sample_chat.id}/active")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 4
        assert all(not msg["is_deleted"] for msg in data)


class TestGetMessagesByType:
    """Tests for GET /messages/chat/{chat_id}/type/{message_type} endpoint."""
    
    def test_get_user_messages_by_type(self, client: TestClient, sample_chat: Chat, multiple_messages: list[Message]):
        """Test getting only user messages."""
        response = client.get(f"{settings.API_V1_STR}/messages/chat/{sample_chat.id}/type/user")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2  # Excludes deleted user message
        assert all(msg["type"] == "user" for msg in data)
    
    def test_get_ai_messages_by_type(self, client: TestClient, sample_chat: Chat, multiple_messages: list[Message]):
        """Test getting only AI messages."""
        response = client.get(f"{settings.API_V1_STR}/messages/chat/{sample_chat.id}/type/ai")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all(msg["type"] == "ai" for msg in data)


class TestGetUserMessages:
    """Tests for GET /messages/chat/{chat_id}/user endpoint."""
    
    def test_get_user_messages(self, client: TestClient, sample_chat: Chat, multiple_messages: list[Message]):
        """Test getting user messages."""
        response = client.get(f"{settings.API_V1_STR}/messages/chat/{sample_chat.id}/user")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all(msg["type"] == "user" for msg in data)


class TestGetAIMessages:
    """Tests for GET /messages/chat/{chat_id}/ai endpoint."""
    
    def test_get_ai_messages(self, client: TestClient, sample_chat: Chat, multiple_messages: list[Message]):
        """Test getting AI messages."""
        response = client.get(f"{settings.API_V1_STR}/messages/chat/{sample_chat.id}/ai")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all(msg["type"] == "ai" for msg in data)


class TestGetLatestMessage:
    """Tests for GET /messages/chat/{chat_id}/latest endpoint."""
    
    def test_get_latest_message(self, client: TestClient, sample_chat: Chat, multiple_messages: list[Message]):
        """Test getting the latest message."""
        response = client.get(f"{settings.API_V1_STR}/messages/chat/{sample_chat.id}/latest")
        
        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "AI response 2"  # Last non-deleted message
    
    def test_get_latest_message_no_messages(self, client: TestClient, sample_chat: Chat):
        """Test getting latest message when none exist."""
        response = client.get(f"{settings.API_V1_STR}/messages/chat/{sample_chat.id}/latest")
        
        assert response.status_code == 404
        assert "No messages" in response.json()["detail"]


class TestCountChatMessages:
    """Tests for GET /messages/chat/{chat_id}/count endpoint."""
    
    def test_count_chat_messages(self, client: TestClient, sample_chat: Chat, multiple_messages: list[Message]):
        """Test counting messages in a chat."""
        response = client.get(f"{settings.API_V1_STR}/messages/chat/{sample_chat.id}/count")
        
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 4  # Excludes deleted by default
    
    def test_count_chat_messages_include_deleted(self, client: TestClient, sample_chat: Chat, multiple_messages: list[Message]):
        """Test counting messages including deleted."""
        response = client.get(f"{settings.API_V1_STR}/messages/chat/{sample_chat.id}/count?include_deleted=true")
        
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 5


class TestGetConversationSummary:
    """Tests for GET /messages/chat/{chat_id}/summary endpoint."""
    
    def test_get_conversation_summary(self, client: TestClient, sample_chat: Chat, multiple_messages: list[Message]):
        """Test getting conversation summary."""
        response = client.get(f"{settings.API_V1_STR}/messages/chat/{sample_chat.id}/summary")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_messages"] == 4
        assert data["user_messages"] == 2
        assert data["ai_messages"] == 2
        assert data["system_messages"] == 0
        assert data["total_tokens"] == 47  # 5+15+7+20
        assert data["total_cost"] > 0
        assert "latest_message_at" in data


class TestGetMessagesWithFeedback:
    """Tests for GET /messages/chat/{chat_id}/feedback endpoint."""
    
    def test_get_messages_with_feedback_empty(self, client: TestClient, sample_chat: Chat, multiple_messages: list[Message]):
        """Test getting messages with feedback when none have feedback."""
        response = client.get(f"{settings.API_V1_STR}/messages/chat/{sample_chat.id}/feedback")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0


class TestGetMessageById:
    """Tests for GET /messages/{message_id} endpoint."""
    
    def test_get_message_by_id_success(self, client: TestClient, sample_message: Message):
        """Test getting a message by ID."""
        response = client.get(f"{settings.API_V1_STR}/messages/{sample_message.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(sample_message.id)
        assert data["content"] == "Hello, this is a test message"
    
    def test_get_message_by_id_not_found(self, client: TestClient):
        """Test getting a non-existent message."""
        fake_id = uuid4()
        response = client.get(f"{settings.API_V1_STR}/messages/{fake_id}")
        
        assert response.status_code == 404
    
    def test_get_message_by_id_other_user(self, client: TestClient, session: Session, other_user_chat: Chat, sample_model: Model):
        """Test getting a message from another user's chat."""
        # Create a message in other user's chat
        message = Message(
            chat_id=other_user_chat.id,
            model_id=sample_model.id,
            type=MessageType.user,
            content="Other user message"
        )
        session.add(message)
        session.commit()
        session.refresh(message)
        
        response = client.get(f"{settings.API_V1_STR}/messages/{message.id}")
        
        assert response.status_code == 404


class TestUpdateMessage:
    """Tests for PUT /messages/{message_id} endpoint."""
    
    def test_update_message_content(self, client: TestClient, sample_message: Message):
        """Test updating message content."""
        update_data = {
            "content": "Updated message content"
        }
        response = client.put(f"{settings.API_V1_STR}/messages/{sample_message.id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "Updated message content"
        assert data["id"] == str(sample_message.id)
    
    def test_update_message_tokens(self, client: TestClient, sample_message: Message):
        """Test updating message tokens."""
        update_data = {
            "tokens": 25
        }
        response = client.put(f"{settings.API_V1_STR}/messages/{sample_message.id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["tokens"] == 25
    
    def test_update_message_feedback(self, client: TestClient, sample_message: Message):
        """Test updating message feedback."""
        update_data = {
            "feedback": "positive"
        }
        response = client.put(f"{settings.API_V1_STR}/messages/{sample_message.id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["feedback"] == "positive"
    
    def test_update_message_not_found(self, client: TestClient):
        """Test updating non-existent message."""
        fake_id = uuid4()
        update_data = {"content": "Test"}
        response = client.put(f"{settings.API_V1_STR}/messages/{fake_id}", json=update_data)
        
        assert response.status_code == 404


class TestUpdateMessageContent:
    """Tests for PATCH /messages/{message_id}/content endpoint."""
    
    def test_update_message_content_success(self, client: TestClient, sample_message: Message):
        """Test updating only message content."""
        response = client.patch(
            f"{settings.API_V1_STR}/messages/{sample_message.id}/content?content=Patched content"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "Patched content"


class TestUpdateMessageFeedback:
    """Tests for PATCH /messages/{message_id}/feedback endpoint."""
    
    def test_update_message_feedback_positive(self, client: TestClient, sample_message: Message):
        """Test updating message feedback to positive."""
        request_data = {
            "feedback": "positive"
        }
        response = client.patch(
            f"{settings.API_V1_STR}/messages/{sample_message.id}/feedback",
            json=request_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["feedback"] == "positive"
    
    def test_update_message_feedback_negative(self, client: TestClient, sample_message: Message):
        """Test updating message feedback to negative."""
        request_data = {
            "feedback": "negative"
        }
        response = client.patch(
            f"{settings.API_V1_STR}/messages/{sample_message.id}/feedback",
            json=request_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["feedback"] == "negative"


class TestDeleteMessage:
    """Tests for DELETE /messages/{message_id} endpoint."""
    
    def test_delete_message_success(self, client: TestClient, sample_message: Message):
        """Test soft deleting a message."""
        response = client.delete(f"{settings.API_V1_STR}/messages/{sample_message.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert "deleted successfully" in data["message"]
    
    def test_delete_message_not_found(self, client: TestClient):
        """Test deleting non-existent message."""
        fake_id = uuid4()
        response = client.delete(f"{settings.API_V1_STR}/messages/{fake_id}")
        
        assert response.status_code == 404


class TestPermanentlyDeleteMessage:
    """Tests for DELETE /messages/{message_id}/permanent endpoint."""
    
    def test_permanently_delete_message_success(self, client: TestClient, sample_message: Message):
        """Test permanently deleting a message."""
        response = client.delete(f"{settings.API_V1_STR}/messages/{sample_message.id}/permanent")
        
        assert response.status_code == 200
        data = response.json()
        assert "permanently deleted" in data["message"]
        
        # Verify message is gone
        get_response = client.get(f"{settings.API_V1_STR}/messages/{sample_message.id}")
        assert get_response.status_code == 404
    
    def test_permanently_delete_message_not_found(self, client: TestClient):
        """Test permanently deleting non-existent message."""
        fake_id = uuid4()
        response = client.delete(f"{settings.API_V1_STR}/messages/{fake_id}/permanent")
        
        assert response.status_code == 404


class TestBulkDeleteMessages:
    """Tests for POST /messages/bulk/delete endpoint."""
    
    def test_bulk_delete_messages_success(self, client: TestClient, multiple_messages: list[Message]):
        """Test bulk soft delete of messages."""
        message_ids = [str(multiple_messages[0].id), str(multiple_messages[1].id)]
        request_data = {
            "message_ids": message_ids
        }
        response = client.post(f"{settings.API_V1_STR}/messages/bulk/delete", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["successful"] == 2
        assert data["failed"] == 0
        assert data["total"] == 2
    
    def test_bulk_delete_messages_partial(self, client: TestClient, multiple_messages: list[Message]):
        """Test bulk delete with some invalid IDs."""
        fake_id = str(uuid4())
        message_ids = [str(multiple_messages[0].id), fake_id]
        request_data = {
            "message_ids": message_ids
        }
        response = client.post(f"{settings.API_V1_STR}/messages/bulk/delete", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        # Only 1 message was accessible and deleted (invalid IDs are filtered out before counting)
        assert data["successful"] == 1
        assert data["total"] == 1
    
    def test_bulk_delete_messages_empty(self, client: TestClient):
        """Test bulk delete with empty list."""
        request_data: dict[str, list[str]] = {
            "message_ids": []
        }
        response = client.post(f"{settings.API_V1_STR}/messages/bulk/delete", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["successful"] == 0
        assert data["failed"] == 0


class TestBulkPermanentlyDeleteMessages:
    """Tests for POST /messages/bulk/delete/permanent endpoint."""
    
    def test_bulk_permanently_delete_messages_success(self, client: TestClient, multiple_messages: list[Message]):
        """Test bulk permanent delete of messages."""
        message_ids = [str(multiple_messages[0].id), str(multiple_messages[1].id)]
        request_data = {
            "message_ids": message_ids
        }
        response = client.post(f"{settings.API_V1_STR}/messages/bulk/delete/permanent", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["successful"] == 2
        assert data["failed"] == 0


class TestDeleteAllChatMessages:
    """Tests for DELETE /messages/chat/{chat_id}/all endpoint."""
    
    def test_delete_all_chat_messages(self, client: TestClient, sample_chat: Chat, multiple_messages: list[Message]):
        """Test deleting all messages in a chat."""
        response = client.delete(f"{settings.API_V1_STR}/messages/chat/{sample_chat.id}/all")
        
        assert response.status_code == 200
        data = response.json()
        assert data["deleted_count"] == 4  # Only active messages
    
    def test_delete_all_chat_messages_empty(self, client: TestClient, sample_chat: Chat):
        """Test deleting all messages in an empty chat."""
        response = client.delete(f"{settings.API_V1_STR}/messages/chat/{sample_chat.id}/all")
        
        assert response.status_code == 200
        data = response.json()
        assert data["deleted_count"] == 0


class TestCheckMessageExists:
    """Tests for GET /messages/{message_id}/exists endpoint."""
    
    def test_check_message_exists_true(self, client: TestClient, sample_message: Message):
        """Test checking existence of an existing message."""
        response = client.get(f"{settings.API_V1_STR}/messages/{sample_message.id}/exists")
        
        assert response.status_code == 200
        data = response.json()
        assert data["exists"] is True
    
    def test_check_message_exists_false(self, client: TestClient):
        """Test checking existence of non-existent message."""
        fake_id = uuid4()
        response = client.get(f"{settings.API_V1_STR}/messages/{fake_id}/exists")
        
        assert response.status_code == 200
        data = response.json()
        assert data["exists"] is False
    
    def test_check_message_exists_other_user(self, client: TestClient, session: Session, other_user_chat: Chat, sample_model: Model):
        """Test checking existence of message in another user's chat."""
        # Create a message in other user's chat
        message = Message(
            chat_id=other_user_chat.id,
            model_id=sample_model.id,
            type=MessageType.user,
            content="Other user message"
        )
        session.add(message)
        session.commit()
        session.refresh(message)
        
        response = client.get(f"{settings.API_V1_STR}/messages/{message.id}/exists")
        
        assert response.status_code == 200
        data = response.json()
        assert data["exists"] is False
