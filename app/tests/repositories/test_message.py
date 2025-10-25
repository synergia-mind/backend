import pytest
from decimal import Decimal
from uuid import uuid4
from sqlmodel import Session

from app.repositories.message import MessageRepository
from app.repositories.model import ModelRepository
from app.repositories.chat import ChatRepository
from app.models import MessageCreate, MessageUpdate, ModelCreate, ChatCreate


@pytest.fixture(name="message_repository")
def message_repository_fixture(session: Session):
    """
    Create a MessageRepository instance with the test session.
    """
    return MessageRepository(session)


@pytest.fixture(name="model_repository")
def model_repository_fixture(session: Session):
    """
    Create a ModelRepository instance with the test session.
    """
    return ModelRepository(session)


@pytest.fixture(name="chat_repository")
def chat_repository_fixture(session: Session):
    """
    Create a ChatRepository instance with the test session.
    """
    return ChatRepository(session)


@pytest.fixture(name="test_model")
def test_model_fixture(model_repository: ModelRepository):
    """
    Create a test model for messages.
    """
    model_data = ModelCreate(
        name="GPT-4",
        provider="OpenAI",
        price_per_million_tokens=Decimal("30.000000")
    )
    return model_repository.create(model_data)


@pytest.fixture(name="test_chat")
def test_chat_fixture(chat_repository: ChatRepository):
    """
    Create a test chat for messages.
    """
    user_id = f"user_{uuid4().hex[:24]}"
    chat_data = ChatCreate(title="Test Chat")
    return chat_repository.create(user_id, chat_data)


@pytest.fixture(name="sample_message_data")
def sample_message_data_fixture(test_chat, test_model):
    """
    Provide sample message creation data.
    """
    return MessageCreate(
        chat_id=test_chat.id,
        model_id=test_model.id,
        type="user",
        content="Hello, this is a test message",
        tokens=10
    )


class TestMessageRepositoryCreate:
    """Tests for the create method."""
    
    def test_create_message_success(self, message_repository: MessageRepository, sample_message_data: MessageCreate):
        """Test creating a new message successfully."""
        message = message_repository.create(sample_message_data)
        
        assert message.id is not None
        assert message.chat_id == sample_message_data.chat_id
        assert message.model_id == sample_message_data.model_id
        assert message.type == "user"
        assert message.content == "Hello, this is a test message"
        assert message.tokens == 10
        assert message.feedback is None
        assert message.is_deleted is False
        assert message.created_at is not None
        assert message.updated_at is not None
    
    def test_create_message_without_tokens(self, message_repository: MessageRepository, test_chat, test_model):
        """Test creating a message without token count."""
        message_data = MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="ai",
            content="Response without tokens"
        )
        
        message = message_repository.create(message_data)
        
        assert message.tokens is None
    
    def test_create_message_different_types(self, message_repository: MessageRepository, test_chat, test_model):
        """Test creating messages with different types."""
        types = ["user", "ai", "system"]
        
        for msg_type in types:
            message_data = MessageCreate(
                chat_id=test_chat.id,
                model_id=test_model.id,
                type=msg_type,
                content=f"Message of type {msg_type}"
            )
            message = message_repository.create(message_data)
            assert message.type == msg_type
    
    def test_create_multiple_messages(self, message_repository: MessageRepository, test_chat, test_model):
        """Test creating multiple messages in the same chat."""
        message1_data = MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="user",
            content="First message"
        )
        message2_data = MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="ai",
            content="Second message"
        )
        
        message1 = message_repository.create(message1_data)
        message2 = message_repository.create(message2_data)
        
        assert message1.id != message2.id
        assert message1.chat_id == message2.chat_id


class TestMessageRepositoryGetById:
    """Tests for the get_by_id method."""
    
    def test_get_by_id_success(self, message_repository: MessageRepository, sample_message_data: MessageCreate):
        """Test retrieving a message by ID successfully."""
        created_message = message_repository.create(sample_message_data)
        
        retrieved_message = message_repository.get_by_id(created_message.id)
        
        assert retrieved_message is not None
        assert retrieved_message.id == created_message.id
        assert retrieved_message.content == created_message.content
    
    def test_get_by_id_not_found(self, message_repository: MessageRepository):
        """Test retrieving a non-existent message by ID."""
        non_existent_id = uuid4()
        
        message = message_repository.get_by_id(non_existent_id)
        
        assert message is None
    
    def test_get_by_id_deleted_message(self, message_repository: MessageRepository, sample_message_data: MessageCreate):
        """Test that soft-deleted messages are not retrieved."""
        created_message = message_repository.create(sample_message_data)
        message_repository.soft_delete(created_message.id)
        
        message = message_repository.get_by_id(created_message.id)
        
        assert message is None


class TestMessageRepositoryGetWithModel:
    """Tests for the get_with_model method."""
    
    def test_get_with_model_success(self, message_repository: MessageRepository, sample_message_data: MessageCreate, test_model):
        """Test retrieving a message with its model successfully."""
        created_message = message_repository.create(sample_message_data)
        
        result = message_repository.get_with_model(created_message.id)
        
        assert result is not None
        message, model = result
        assert message.id == created_message.id
        assert model.id == test_model.id
        assert model.name == "GPT-4"
    
    def test_get_with_model_not_found(self, message_repository: MessageRepository):
        """Test retrieving a non-existent message with model."""
        non_existent_id = uuid4()
        
        result = message_repository.get_with_model(non_existent_id)
        
        assert result is None
    
    def test_get_with_model_deleted_message(self, message_repository: MessageRepository, sample_message_data: MessageCreate):
        """Test that deleted messages are not retrieved with model."""
        created_message = message_repository.create(sample_message_data)
        message_repository.soft_delete(created_message.id)
        
        result = message_repository.get_with_model(created_message.id)
        
        assert result is None


class TestMessageRepositoryGetAllByChat:
    """Tests for the get_all_by_chat method."""
    
    def test_get_all_by_chat_empty(self, message_repository: MessageRepository, test_chat):
        """Test retrieving all messages for a chat with no messages."""
        messages = message_repository.get_all_by_chat(test_chat.id)
        
        assert messages == []
    
    def test_get_all_by_chat_with_messages(self, message_repository: MessageRepository, test_chat, test_model):
        """Test retrieving all messages for a chat."""
        message1_data = MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="user",
            content="First message"
        )
        message2_data = MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="ai",
            content="Second message"
        )
        
        message_repository.create(message1_data)
        message_repository.create(message2_data)
        
        messages = message_repository.get_all_by_chat(test_chat.id)
        
        assert len(messages) == 2
    
    def test_get_all_by_chat_with_pagination(self, message_repository: MessageRepository, test_chat, test_model):
        """Test pagination with skip and limit."""
        for i in range(5):
            message_data = MessageCreate(
                chat_id=test_chat.id,
                model_id=test_model.id,
                type="user",
                content=f"Message {i}"
            )
            message_repository.create(message_data)
        
        # Test skip
        messages = message_repository.get_all_by_chat(test_chat.id, skip=2)
        assert len(messages) == 3
        
        # Test limit
        messages = message_repository.get_all_by_chat(test_chat.id, limit=2)
        assert len(messages) == 2
        
        # Test skip and limit together
        messages = message_repository.get_all_by_chat(test_chat.id, skip=1, limit=2)
        assert len(messages) == 2
    
    def test_get_all_by_chat_excludes_deleted(self, message_repository: MessageRepository, test_chat, test_model):
        """Test that deleted messages are excluded by default."""
        message1_data = MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="user",
            content="Active message"
        )
        message2_data = MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="user",
            content="Deleted message"
        )
        
        message1 = message_repository.create(message1_data)
        message2 = message_repository.create(message2_data)
        
        # Soft delete message2
        message_repository.soft_delete(message2.id)
        
        messages = message_repository.get_all_by_chat(test_chat.id)
        
        assert len(messages) == 1
        assert messages[0].content == "Active message"
    
    def test_get_all_by_chat_include_deleted(self, message_repository: MessageRepository, test_chat, test_model):
        """Test retrieving all messages including deleted ones."""
        message1_data = MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="user",
            content="Active message"
        )
        message2_data = MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="user",
            content="Deleted message"
        )
        
        message1 = message_repository.create(message1_data)
        message2 = message_repository.create(message2_data)
        
        # Soft delete message2
        message_repository.soft_delete(message2.id)
        
        messages = message_repository.get_all_by_chat(test_chat.id, include_deleted=True)
        
        assert len(messages) == 2
    
    def test_get_all_by_chat_ordered_by_created_at(self, message_repository: MessageRepository, test_chat, test_model):
        """Test that messages are ordered by created_at ascending (oldest first)."""
        message1 = message_repository.create(MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="user",
            content="First message"
        ))
        message2 = message_repository.create(MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="ai",
            content="Second message"
        ))
        message3 = message_repository.create(MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="user",
            content="Third message"
        ))
        
        messages = message_repository.get_all_by_chat(test_chat.id)
        
        # Oldest should be first
        assert messages[0].id == message1.id
        assert messages[1].id == message2.id
        assert messages[2].id == message3.id
    
    def test_get_all_by_chat_isolation(self, message_repository: MessageRepository, chat_repository: ChatRepository, test_model):
        """Test that messages are isolated by chat."""
        user_id = f"user_{uuid4().hex[:24]}"
        chat1 = chat_repository.create(user_id, ChatCreate(title="Chat 1"))
        chat2 = chat_repository.create(user_id, ChatCreate(title="Chat 2"))
        
        message_repository.create(MessageCreate(
            chat_id=chat1.id,
            model_id=test_model.id,
            type="user",
            content="Chat 1 message"
        ))
        message_repository.create(MessageCreate(
            chat_id=chat2.id,
            model_id=test_model.id,
            type="user",
            content="Chat 2 message"
        ))
        
        chat1_messages = message_repository.get_all_by_chat(chat1.id)
        chat2_messages = message_repository.get_all_by_chat(chat2.id)
        
        assert len(chat1_messages) == 1
        assert len(chat2_messages) == 1
        assert chat1_messages[0].content == "Chat 1 message"
        assert chat2_messages[0].content == "Chat 2 message"


class TestMessageRepositoryGetAllByChatWithModel:
    """Tests for the get_all_by_chat_with_model method."""
    
    def test_get_all_by_chat_with_model_success(self, message_repository: MessageRepository, test_chat, test_model):
        """Test retrieving all messages with their models."""
        message_repository.create(MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="user",
            content="Test message"
        ))
        
        results = message_repository.get_all_by_chat_with_model(test_chat.id)
        
        assert len(results) == 1
        message, model = results[0]
        assert message.content == "Test message"
        assert model.name == "GPT-4"
    
    def test_get_all_by_chat_with_model_multiple_models(
        self, 
        message_repository: MessageRepository, 
        model_repository: ModelRepository,
        test_chat, 
        test_model
    ):
        """Test retrieving messages with different models."""
        model2 = model_repository.create(ModelCreate(
            name="Claude-3",
            provider="Anthropic",
            price_per_million_tokens=Decimal("15.000000")
        ))
        
        message_repository.create(MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="user",
            content="GPT-4 message"
        ))
        message_repository.create(MessageCreate(
            chat_id=test_chat.id,
            model_id=model2.id,
            type="ai",
            content="Claude-3 message"
        ))
        
        results = message_repository.get_all_by_chat_with_model(test_chat.id)
        
        assert len(results) == 2
        assert results[0][1].name == "GPT-4"
        assert results[1][1].name == "Claude-3"


class TestMessageRepositoryGetByType:
    """Tests for the get_by_type method."""
    
    def test_get_by_type_success(self, message_repository: MessageRepository, test_chat, test_model):
        """Test retrieving messages by type."""
        message_repository.create(MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="user",
            content="User message 1"
        ))
        message_repository.create(MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="ai",
            content="AI message"
        ))
        message_repository.create(MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="user",
            content="User message 2"
        ))
        
        user_messages = message_repository.get_by_type(test_chat.id, "user")
        
        assert len(user_messages) == 2
        assert all(msg.type == "user" for msg in user_messages)
    
    def test_get_by_type_with_pagination(self, message_repository: MessageRepository, test_chat, test_model):
        """Test pagination when getting messages by type."""
        for i in range(5):
            message_repository.create(MessageCreate(
                chat_id=test_chat.id,
                model_id=test_model.id,
                type="user",
                content=f"Message {i}"
            ))
        
        messages = message_repository.get_by_type(test_chat.id, "user", skip=1, limit=2)
        
        assert len(messages) == 2
    
    def test_get_by_type_excludes_deleted(self, message_repository: MessageRepository, test_chat, test_model):
        """Test that deleted messages are excluded."""
        message1 = message_repository.create(MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="user",
            content="Active"
        ))
        message2 = message_repository.create(MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="user",
            content="Deleted"
        ))
        
        message_repository.soft_delete(message2.id)
        
        messages = message_repository.get_by_type(test_chat.id, "user")
        
        assert len(messages) == 1
        assert messages[0].content == "Active"


class TestMessageRepositoryUpdate:
    """Tests for the update method."""
    
    def test_update_message_success(self, message_repository: MessageRepository, sample_message_data: MessageCreate):
        """Test updating a message successfully."""
        created_message = message_repository.create(sample_message_data)
        original_updated_at = created_message.updated_at
        
        update_data = MessageUpdate(
            content="Updated content",
            tokens=20
        )
        
        updated_message = message_repository.update(created_message.id, update_data)
        
        assert updated_message is not None
        assert updated_message.content == "Updated content"
        assert updated_message.tokens == 20
        assert updated_message.updated_at > original_updated_at
    
    def test_update_message_not_found(self, message_repository: MessageRepository):
        """Test updating a non-existent message."""
        non_existent_id = uuid4()
        update_data = MessageUpdate(content="New content")
        
        result = message_repository.update(non_existent_id, update_data)
        
        assert result is None
    
    def test_update_partial_fields(self, message_repository: MessageRepository, sample_message_data: MessageCreate):
        """Test updating only specific fields."""
        created_message = message_repository.create(sample_message_data)
        
        # Only update content
        update_data = MessageUpdate(content="Only content updated")
        updated_message = message_repository.update(created_message.id, update_data)
        
        assert updated_message is not None
        assert updated_message.content == "Only content updated"
        assert updated_message.tokens == created_message.tokens  # Unchanged
    
    def test_update_deleted_message(self, message_repository: MessageRepository, sample_message_data: MessageCreate):
        """Test that deleted messages cannot be updated."""
        created_message = message_repository.create(sample_message_data)
        message_repository.soft_delete(created_message.id)
        
        update_data = MessageUpdate(content="Should not update")
        result = message_repository.update(created_message.id, update_data)
        
        assert result is None


class TestMessageRepositoryUpdateFeedback:
    """Tests for the update_feedback method."""
    
    def test_update_feedback_success(self, message_repository: MessageRepository, sample_message_data: MessageCreate):
        """Test updating message feedback successfully."""
        created_message = message_repository.create(sample_message_data)
        
        updated_message = message_repository.update_feedback(created_message.id, "positive")
        
        assert updated_message is not None
        assert updated_message.feedback == "positive"
    
    def test_update_feedback_to_negative(self, message_repository: MessageRepository, sample_message_data: MessageCreate):
        """Test updating feedback to negative."""
        created_message = message_repository.create(sample_message_data)
        
        updated_message = message_repository.update_feedback(created_message.id, "negative")
        
        assert updated_message is not None
        assert updated_message.feedback == "negative"
    
    def test_update_feedback_not_found(self, message_repository: MessageRepository):
        """Test updating feedback for a non-existent message."""
        non_existent_id = uuid4()
        
        result = message_repository.update_feedback(non_existent_id, "positive")
        
        assert result is None
    
    def test_update_feedback_updates_timestamp(self, message_repository: MessageRepository, sample_message_data: MessageCreate):
        """Test that updating feedback updates the timestamp."""
        created_message = message_repository.create(sample_message_data)
        original_updated_at = created_message.updated_at
        
        updated_message = message_repository.update_feedback(created_message.id, "positive")
        
        assert updated_message is not None
        assert updated_message.updated_at > original_updated_at


class TestMessageRepositorySoftDelete:
    """Tests for the soft_delete method."""
    
    def test_soft_delete_success(self, message_repository: MessageRepository, sample_message_data: MessageCreate):
        """Test soft deleting a message successfully."""
        created_message = message_repository.create(sample_message_data)
        
        result = message_repository.soft_delete(created_message.id)
        
        assert result is True
        
        # Verify it's marked as deleted
        message = message_repository.get_by_id(created_message.id)
        assert message is None
    
    def test_soft_delete_not_found(self, message_repository: MessageRepository):
        """Test soft deleting a non-existent message."""
        non_existent_id = uuid4()
        
        result = message_repository.soft_delete(non_existent_id)
        
        assert result is False
    
    def test_soft_delete_already_deleted(self, message_repository: MessageRepository, sample_message_data: MessageCreate):
        """Test soft deleting an already deleted message."""
        created_message = message_repository.create(sample_message_data)
        
        # First deletion
        result1 = message_repository.soft_delete(created_message.id)
        assert result1 is True
        
        # Second deletion should fail (not found)
        result2 = message_repository.soft_delete(created_message.id)
        assert result2 is False


class TestMessageRepositoryHardDelete:
    """Tests for the hard_delete method."""
    
    def test_hard_delete_success(self, message_repository: MessageRepository, sample_message_data: MessageCreate, test_chat):
        """Test hard deleting a message successfully."""
        created_message = message_repository.create(sample_message_data)
        
        result = message_repository.hard_delete(created_message.id)
        
        assert result is True
        
        # Verify it's completely removed
        messages = message_repository.get_all_by_chat(test_chat.id, include_deleted=True)
        assert len(messages) == 0
    
    def test_hard_delete_not_found(self, message_repository: MessageRepository):
        """Test hard deleting a non-existent message."""
        non_existent_id = uuid4()
        
        result = message_repository.hard_delete(non_existent_id)
        
        assert result is False
    
    def test_hard_delete_soft_deleted_message(self, message_repository: MessageRepository, sample_message_data: MessageCreate):
        """Test hard deleting a soft-deleted message."""
        created_message = message_repository.create(sample_message_data)
        
        # First soft delete
        message_repository.soft_delete(created_message.id)
        
        # Then hard delete
        result = message_repository.hard_delete(created_message.id)
        
        assert result is True


class TestMessageRepositorySoftDeleteByChat:
    """Tests for the soft_delete_by_chat method."""
    
    def test_soft_delete_by_chat_success(self, message_repository: MessageRepository, test_chat, test_model):
        """Test soft deleting all messages in a chat."""
        for i in range(3):
            message_repository.create(MessageCreate(
                chat_id=test_chat.id,
                model_id=test_model.id,
                type="user",
                content=f"Message {i}"
            ))
        
        count = message_repository.soft_delete_by_chat(test_chat.id)
        
        assert count == 3
        
        # Verify all messages are deleted
        messages = message_repository.get_all_by_chat(test_chat.id)
        assert len(messages) == 0
    
    def test_soft_delete_by_chat_empty(self, message_repository: MessageRepository, test_chat):
        """Test soft deleting messages in a chat with no messages."""
        count = message_repository.soft_delete_by_chat(test_chat.id)
        
        assert count == 0
    
    def test_soft_delete_by_chat_excludes_already_deleted(self, message_repository: MessageRepository, test_chat, test_model):
        """Test that already deleted messages are not counted."""
        message1 = message_repository.create(MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="user",
            content="Active"
        ))
        message2 = message_repository.create(MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="user",
            content="Already deleted"
        ))
        
        # Soft delete message2 first
        message_repository.soft_delete(message2.id)
        
        # Now soft delete by chat
        count = message_repository.soft_delete_by_chat(test_chat.id)
        
        assert count == 1  # Only message1 was deleted


class TestMessageRepositoryCountByChat:
    """Tests for the count_by_chat method."""
    
    def test_count_by_chat_empty(self, message_repository: MessageRepository, test_chat):
        """Test counting messages in a chat with no messages."""
        count = message_repository.count_by_chat(test_chat.id)
        
        assert count == 0
    
    def test_count_by_chat_with_messages(self, message_repository: MessageRepository, test_chat, test_model):
        """Test counting messages in a chat."""
        for i in range(3):
            message_repository.create(MessageCreate(
                chat_id=test_chat.id,
                model_id=test_model.id,
                type="user",
                content=f"Message {i}"
            ))
        
        count = message_repository.count_by_chat(test_chat.id)
        
        assert count == 3
    
    def test_count_by_chat_excludes_deleted(self, message_repository: MessageRepository, test_chat, test_model):
        """Test that deleted messages are excluded from count by default."""
        message1 = message_repository.create(MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="user",
            content="Active"
        ))
        message2 = message_repository.create(MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="user",
            content="Deleted"
        ))
        
        message_repository.soft_delete(message2.id)
        
        count = message_repository.count_by_chat(test_chat.id)
        
        assert count == 1
    
    def test_count_by_chat_include_deleted(self, message_repository: MessageRepository, test_chat, test_model):
        """Test counting messages including deleted ones."""
        message1 = message_repository.create(MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="user",
            content="Active"
        ))
        message2 = message_repository.create(MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="user",
            content="Deleted"
        ))
        
        message_repository.soft_delete(message2.id)
        
        count = message_repository.count_by_chat(test_chat.id, include_deleted=True)
        
        assert count == 2


class TestMessageRepositoryGetLatestByChat:
    """Tests for the get_latest_by_chat method."""
    
    def test_get_latest_by_chat_success(self, message_repository: MessageRepository, test_chat, test_model):
        """Test retrieving the latest message in a chat."""
        message1 = message_repository.create(MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="user",
            content="First message"
        ))
        message2 = message_repository.create(MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="ai",
            content="Latest message"
        ))
        
        latest = message_repository.get_latest_by_chat(test_chat.id)
        
        assert latest is not None
        assert latest.id == message2.id
        assert latest.content == "Latest message"
    
    def test_get_latest_by_chat_empty(self, message_repository: MessageRepository, test_chat):
        """Test getting latest message from an empty chat."""
        latest = message_repository.get_latest_by_chat(test_chat.id)
        
        assert latest is None
    
    def test_get_latest_by_chat_excludes_deleted(self, message_repository: MessageRepository, test_chat, test_model):
        """Test that deleted messages are excluded."""
        message1 = message_repository.create(MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="user",
            content="Older message"
        ))
        message2 = message_repository.create(MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="ai",
            content="Latest but deleted"
        ))
        
        message_repository.soft_delete(message2.id)
        
        latest = message_repository.get_latest_by_chat(test_chat.id)
        
        assert latest is not None
        assert latest.id == message1.id


class TestMessageRepositoryCalculateTotalTokens:
    """Tests for the calculate_total_tokens method."""
    
    def test_calculate_total_tokens_success(self, message_repository: MessageRepository, test_chat, test_model):
        """Test calculating total tokens for a chat."""
        message_repository.create(MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="user",
            content="Message 1",
            tokens=10
        ))
        message_repository.create(MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="ai",
            content="Message 2",
            tokens=20
        ))
        message_repository.create(MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="user",
            content="Message 3",
            tokens=15
        ))
        
        total_tokens = message_repository.calculate_total_tokens(test_chat.id)
        
        assert total_tokens == 45
    
    def test_calculate_total_tokens_empty(self, message_repository: MessageRepository, test_chat):
        """Test calculating tokens for an empty chat."""
        total_tokens = message_repository.calculate_total_tokens(test_chat.id)
        
        assert total_tokens == 0
    
    def test_calculate_total_tokens_with_none_values(self, message_repository: MessageRepository, test_chat, test_model):
        """Test calculating tokens when some messages have None tokens."""
        message_repository.create(MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="user",
            content="With tokens",
            tokens=10
        ))
        message_repository.create(MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="ai",
            content="Without tokens"
            # tokens is None
        ))
        
        total_tokens = message_repository.calculate_total_tokens(test_chat.id)
        
        assert total_tokens == 10
    
    def test_calculate_total_tokens_excludes_deleted(self, message_repository: MessageRepository, test_chat, test_model):
        """Test that deleted messages are excluded from token calculation."""
        message1 = message_repository.create(MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="user",
            content="Active",
            tokens=10
        ))
        message2 = message_repository.create(MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="ai",
            content="Deleted",
            tokens=20
        ))
        
        message_repository.soft_delete(message2.id)
        
        total_tokens = message_repository.calculate_total_tokens(test_chat.id)
        
        assert total_tokens == 10


class TestMessageRepositoryIntegration:
    """Integration tests combining multiple repository operations."""
    
    def test_full_crud_cycle(self, message_repository: MessageRepository, test_chat, test_model):
        """Test a complete CRUD cycle."""
        # Create
        message_data = MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="user",
            content="Test message",
            tokens=10
        )
        created_message = message_repository.create(message_data)
        assert created_message.id is not None
        
        # Read
        retrieved_message = message_repository.get_by_id(created_message.id)
        assert retrieved_message is not None
        assert retrieved_message.content == "Test message"
        
        # Update
        update_data = MessageUpdate(content="Updated message", tokens=15)
        updated_message = message_repository.update(created_message.id, update_data)
        assert updated_message is not None
        assert updated_message.content == "Updated message"
        assert updated_message.tokens == 15
        
        # Update feedback
        feedback_message = message_repository.update_feedback(created_message.id, "positive")
        assert feedback_message is not None
        assert feedback_message.feedback == "positive"
        
        # Soft Delete
        delete_result = message_repository.soft_delete(created_message.id)
        assert delete_result is True
        
        # Verify soft deletion
        deleted_message = message_repository.get_by_id(created_message.id)
        assert deleted_message is None
        
        # Hard Delete
        hard_delete_result = message_repository.hard_delete(created_message.id)
        assert hard_delete_result is True
    
    def test_complex_conversation_scenario(self, message_repository: MessageRepository, test_chat, test_model):
        """Test a complex conversation scenario."""
        # Create a conversation
        user_msg1 = message_repository.create(MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="user",
            content="Hello",
            tokens=5
        ))
        ai_msg1 = message_repository.create(MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="ai",
            content="Hi there!",
            tokens=10
        ))
        user_msg2 = message_repository.create(MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="user",
            content="How are you?",
            tokens=8
        ))
        ai_msg2 = message_repository.create(MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="ai",
            content="I'm doing well!",
            tokens=12
        ))
        
        # Verify count
        assert message_repository.count_by_chat(test_chat.id) == 4
        
        # Get user messages only
        user_messages = message_repository.get_by_type(test_chat.id, "user")
        assert len(user_messages) == 2
        
        # Get AI messages only
        ai_messages = message_repository.get_by_type(test_chat.id, "ai")
        assert len(ai_messages) == 2
        
        # Calculate total tokens
        total_tokens = message_repository.calculate_total_tokens(test_chat.id)
        assert total_tokens == 35
        
        # Get latest message
        latest = message_repository.get_latest_by_chat(test_chat.id)
        assert latest is not None
        assert latest.id == ai_msg2.id
        
        # Add feedback to AI response
        message_repository.update_feedback(ai_msg1.id, "positive")
        
        # Delete one message
        message_repository.soft_delete(user_msg2.id)
        
        # Verify count after deletion
        assert message_repository.count_by_chat(test_chat.id) == 3
        
        # Verify token count excludes deleted message
        total_tokens_after = message_repository.calculate_total_tokens(test_chat.id)
        assert total_tokens_after == 27
    
    def test_multi_chat_isolation(
        self, 
        message_repository: MessageRepository, 
        chat_repository: ChatRepository,
        test_model
    ):
        """Test that messages are properly isolated between chats."""
        user_id = f"user_{uuid4().hex[:24]}"
        chat1 = chat_repository.create(user_id, ChatCreate(title="Chat 1"))
        chat2 = chat_repository.create(user_id, ChatCreate(title="Chat 2"))
        
        # Add messages to both chats
        message_repository.create(MessageCreate(
            chat_id=chat1.id,
            model_id=test_model.id,
            type="user",
            content="Chat 1 message",
            tokens=10
        ))
        message_repository.create(MessageCreate(
            chat_id=chat2.id,
            model_id=test_model.id,
            type="user",
            content="Chat 2 message",
            tokens=20
        ))
        
        # Verify isolation
        chat1_messages = message_repository.get_all_by_chat(chat1.id)
        chat2_messages = message_repository.get_all_by_chat(chat2.id)
        
        assert len(chat1_messages) == 1
        assert len(chat2_messages) == 1
        
        # Verify token calculations are isolated
        chat1_tokens = message_repository.calculate_total_tokens(chat1.id)
        chat2_tokens = message_repository.calculate_total_tokens(chat2.id)
        
        assert chat1_tokens == 10
        assert chat2_tokens == 20
        
        # Soft delete all messages in chat1
        deleted_count = message_repository.soft_delete_by_chat(chat1.id)
        assert deleted_count == 1
        
        # Verify chat2 is unaffected
        assert message_repository.count_by_chat(chat2.id) == 1
