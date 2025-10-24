# type: ignore
import pytest
from decimal import Decimal
from uuid import uuid4, UUID
from sqlmodel import Session

from app.services.message import MessageService
from app.services.chat import ChatService
from app.services.model import ModelService
from app.models import MessageCreate, MessageUpdate, ModelCreate, ChatCreate


@pytest.fixture
def message_service(session: Session):
    """Create a MessageService instance with test session."""
    return MessageService(session)


@pytest.fixture
def chat_service(session: Session):
    """Create a ChatService instance with test session."""
    return ChatService(session)


@pytest.fixture
def model_service(session: Session):
    """Create a ModelService instance with test session."""
    return ModelService(session)


@pytest.fixture
def user_id() -> UUID:
    """Sample user ID."""
    return uuid4()


@pytest.fixture
def test_model(model_service: ModelService):
    """Create a test model."""
    model_data = ModelCreate(
        name="test-gpt-4",
        provider="openai",
        price_per_million_tokens=Decimal("30.00"),
        is_enabled=True
    )
    return model_service.create_model(model_data)


@pytest.fixture
def disabled_model(model_service: ModelService):
    """Create a disabled test model."""
    model_data = ModelCreate(
        name="disabled-model",
        provider="test",
        price_per_million_tokens=Decimal("10.00"),
        is_enabled=False
    )
    return model_service.create_model(model_data)


@pytest.fixture
def test_chat(chat_service: ChatService, user_id: UUID):
    """Create a test chat."""
    chat_data = ChatCreate(title="Test Chat")
    return chat_service.create_chat(user_id, chat_data)


@pytest.fixture
def sample_message_data(test_chat, test_model):
    """Sample message creation data."""
    return MessageCreate(
        chat_id=test_chat.id,
        model_id=test_model.id,
        type="user",
        content="Hello, this is a test message",
        tokens=10
    )


class TestCreateMessage:
    """Tests for create_message method."""
    
    def test_create_message_success(
        self,
        message_service: MessageService,
        sample_message_data: MessageCreate
    ):
        """Test successful message creation."""
        result = message_service.create_message(sample_message_data)
        
        assert result is not None
        assert result.content == sample_message_data.content
        assert result.type == sample_message_data.type
        assert result.tokens == sample_message_data.tokens
        assert result.chat_id == sample_message_data.chat_id
        assert result.model_id == sample_message_data.model_id
        assert result.is_deleted is False
        assert result.id is not None
        assert result.created_at is not None
        assert result.model is not None
    
    def test_create_message_with_disabled_model(
        self,
        message_service: MessageService,
        test_chat,
        disabled_model
    ):
        """Test creating message with disabled model raises ValueError."""
        message_data = MessageCreate(
            chat_id=test_chat.id,
            model_id=disabled_model.id,
            type="user",
            content="Test"
        )
        
        with pytest.raises(ValueError, match="is currently disabled"):
            message_service.create_message(message_data)
    
    def test_create_message_with_nonexistent_model(
        self,
        message_service: MessageService,
        test_chat
    ):
        """Test creating message with non-existent model raises ValueError."""
        message_data = MessageCreate(
            chat_id=test_chat.id,
            model_id=uuid4(),
            type="user",
            content="Test"
        )
        
        with pytest.raises(ValueError, match="does not exist"):
            message_service.create_message(message_data)
    
    def test_create_message_with_nonexistent_chat(
        self,
        message_service: MessageService,
        test_model
    ):
        """Test creating message with non-existent chat raises ValueError."""
        message_data = MessageCreate(
            chat_id=uuid4(),
            model_id=test_model.id,
            type="user",
            content="Test"
        )
        
        with pytest.raises(ValueError, match="Chat with ID .* does not exist"):
            message_service.create_message(message_data)
    
    def test_create_message_without_tokens(
        self,
        message_service: MessageService,
        test_chat,
        test_model
    ):
        """Test creating message without token count."""
        message_data = MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="user",
            content="Test without tokens"
        )
        
        result = message_service.create_message(message_data)
        
        assert result is not None
        assert result.tokens is None


class TestCreateMessageWithAutoChat:
    """Tests for create_message_with_auto_chat method."""
    
    def test_create_message_with_auto_chat_success(
        self,
        message_service: MessageService,
        user_id: UUID,
        test_model
    ):
        """Test creating message with auto-created chat."""
        result, chat_id = message_service.create_message_with_auto_chat(
            user_id=user_id,
            model_id=test_model.id,
            content="This is a new conversation starter",
            message_type="user",
            tokens=8
        )
        
        assert result is not None
        assert result.content == "This is a new conversation starter"
        assert result.type == "user"
        assert result.tokens == 8
        assert result.chat_id == chat_id
        assert chat_id is not None
    
    def test_create_message_with_auto_chat_custom_title(
        self,
        message_service: MessageService,
        chat_service: ChatService,
        user_id: UUID,
        test_model
    ):
        """Test creating message with custom chat title."""
        result, chat_id = message_service.create_message_with_auto_chat(
            user_id=user_id,
            model_id=test_model.id,
            content="Test content",
            chat_title="Custom Title"
        )
        
        chat = chat_service.get_chat_by_id(chat_id, user_id)
        assert chat is not None
        assert chat.title == "Custom Title"
    
    def test_create_message_with_auto_chat_long_content(
        self,
        message_service: MessageService,
        chat_service: ChatService,
        user_id: UUID,
        test_model
    ):
        """Test that long content is truncated for chat title."""
        long_content = "A" * 100
        result, chat_id = message_service.create_message_with_auto_chat(
            user_id=user_id,
            model_id=test_model.id,
            content=long_content
        )
        
        chat = chat_service.get_chat_by_id(chat_id, user_id)
        assert chat is not None
        assert len(chat.title) == 53  # 50 chars + "..."
        assert chat.title.endswith("...")
    
    def test_create_message_with_auto_chat_disabled_model(
        self,
        message_service: MessageService,
        user_id: UUID,
        disabled_model
    ):
        """Test creating message with disabled model raises ValueError."""
        with pytest.raises(ValueError, match="is currently disabled"):
            message_service.create_message_with_auto_chat(
                user_id=user_id,
                model_id=disabled_model.id,
                content="Test"
            )


class TestGetMessageById:
    """Tests for get_message_by_id method."""
    
    def test_get_message_by_id_success(
        self,
        message_service: MessageService,
        sample_message_data: MessageCreate
    ):
        """Test successful retrieval by ID."""
        created = message_service.create_message(sample_message_data)
        
        result = message_service.get_message_by_id(created.id)
        
        assert result is not None
        assert result.id == created.id
        assert result.content == created.content
        assert result.model is not None
    
    def test_get_message_by_id_not_found(self, message_service: MessageService):
        """Test retrieval with non-existent ID returns None."""
        result = message_service.get_message_by_id(uuid4())
        
        assert result is None


class TestGetChatMessages:
    """Tests for get_chat_messages method."""
    
    def test_get_chat_messages_empty(
        self,
        message_service: MessageService,
        test_chat
    ):
        """Test getting messages when none exist."""
        result = message_service.get_chat_messages(test_chat.id)
        
        assert result == []
    
    def test_get_chat_messages_success(
        self,
        message_service: MessageService,
        test_chat,
        test_model
    ):
        """Test getting all messages for a chat."""
        # Create multiple messages
        for i in range(3):
            message_data = MessageCreate(
                chat_id=test_chat.id,
                model_id=test_model.id,
                type="user",
                content=f"Message {i}"
            )
            message_service.create_message(message_data)
        
        result = message_service.get_chat_messages(test_chat.id)
        
        assert len(result) == 3
    
    def test_get_chat_messages_pagination(
        self,
        message_service: MessageService,
        test_chat,
        test_model
    ):
        """Test pagination."""
        # Create multiple messages
        for i in range(3):
            message_data = MessageCreate(
                chat_id=test_chat.id,
                model_id=test_model.id,
                type="user",
                content=f"Message {i}"
            )
            message_service.create_message(message_data)
        
        result = message_service.get_chat_messages(test_chat.id, skip=0, limit=2)
        assert len(result) == 2
        
        result = message_service.get_chat_messages(test_chat.id, skip=2, limit=2)
        assert len(result) == 1
    
    def test_get_chat_messages_excludes_deleted(
        self,
        message_service: MessageService,
        test_chat,
        test_model
    ):
        """Test that deleted messages are excluded by default."""
        msg1_data = MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="user",
            content="Message 1"
        )
        msg1 = message_service.create_message(msg1_data)
        
        msg2_data = MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="user",
            content="Message 2"
        )
        message_service.create_message(msg2_data)
        
        # Delete one message
        message_service.delete_message(msg1.id)
        
        result = message_service.get_chat_messages(test_chat.id)
        
        assert len(result) == 1
    
    def test_get_chat_messages_include_deleted(
        self,
        message_service: MessageService,
        test_chat,
        test_model
    ):
        """Test including deleted messages."""
        msg1_data = MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="user",
            content="Message 1"
        )
        msg1 = message_service.create_message(msg1_data)
        
        msg2_data = MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="user",
            content="Message 2"
        )
        message_service.create_message(msg2_data)
        
        # Delete one message
        message_service.delete_message(msg1.id)
        
        result = message_service.get_chat_messages(test_chat.id, include_deleted=True)
        
        assert len(result) == 2


class TestGetActiveMessages:
    """Tests for get_active_messages method."""
    
    def test_get_active_messages(
        self,
        message_service: MessageService,
        test_chat,
        test_model
    ):
        """Test getting only active messages."""
        msg1_data = MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="user",
            content="Message 1"
        )
        msg1 = message_service.create_message(msg1_data)
        
        msg2_data = MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="user",
            content="Message 2"
        )
        message_service.create_message(msg2_data)
        
        # Delete one message
        message_service.delete_message(msg1.id)
        
        result = message_service.get_active_messages(test_chat.id)
        
        assert len(result) == 1


class TestGetMessagesByType:
    """Tests for get_messages_by_type method."""
    
    def test_get_messages_by_type(
        self,
        message_service: MessageService,
        test_chat,
        test_model
    ):
        """Test getting messages filtered by type."""
        # Create user message
        user_msg = MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="user",
            content="User message"
        )
        message_service.create_message(user_msg)
        
        # Create AI message
        ai_msg = MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="ai",
            content="AI message"
        )
        message_service.create_message(ai_msg)
        
        user_messages = message_service.get_messages_by_type(test_chat.id, "user")
        ai_messages = message_service.get_messages_by_type(test_chat.id, "ai")
        
        assert len(user_messages) == 1
        assert len(ai_messages) == 1
        assert user_messages[0].type == "user"
        assert ai_messages[0].type == "ai"


class TestGetUserMessages:
    """Tests for get_user_messages method."""
    
    def test_get_user_messages(
        self,
        message_service: MessageService,
        test_chat,
        test_model
    ):
        """Test getting only user messages."""
        # Create user message
        user_msg = MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="user",
            content="User message"
        )
        message_service.create_message(user_msg)
        
        # Create AI message
        ai_msg = MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="ai",
            content="AI message"
        )
        message_service.create_message(ai_msg)
        
        result = message_service.get_user_messages(test_chat.id)
        
        assert len(result) == 1
        assert result[0].type == "user"


class TestGetAiMessages:
    """Tests for get_ai_messages method."""
    
    def test_get_ai_messages(
        self,
        message_service: MessageService,
        test_chat,
        test_model
    ):
        """Test getting only AI messages."""
        # Create user message
        user_msg = MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="user",
            content="User message"
        )
        message_service.create_message(user_msg)
        
        # Create AI message
        ai_msg = MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="ai",
            content="AI message"
        )
        message_service.create_message(ai_msg)
        
        result = message_service.get_ai_messages(test_chat.id)
        
        assert len(result) == 1
        assert result[0].type == "ai"


class TestUpdateMessage:
    """Tests for update_message method."""
    
    def test_update_message_success(
        self,
        message_service: MessageService,
        sample_message_data: MessageCreate
    ):
        """Test successful message update."""
        created = message_service.create_message(sample_message_data)
        
        update_data = MessageUpdate(
            content="Updated content",
            tokens=15
        )
        result = message_service.update_message(created.id, update_data)
        
        assert result is not None
        assert result.content == "Updated content"
        assert result.tokens == 15
    
    def test_update_message_not_found(self, message_service: MessageService):
        """Test updating non-existent message returns None."""
        update_data = MessageUpdate(content="New content")
        result = message_service.update_message(uuid4(), update_data)
        
        assert result is None
    
    def test_update_message_to_disabled_model(
        self,
        message_service: MessageService,
        sample_message_data: MessageCreate,
        disabled_model
    ):
        """Test updating to disabled model raises ValueError."""
        created = message_service.create_message(sample_message_data)
        
        update_data = MessageUpdate(model_id=disabled_model.id)
        
        with pytest.raises(ValueError, match="is currently disabled"):
            message_service.update_message(created.id, update_data)


class TestUpdateMessageContent:
    """Tests for update_message_content method."""
    
    def test_update_message_content_success(
        self,
        message_service: MessageService,
        sample_message_data: MessageCreate
    ):
        """Test updating only message content."""
        created = message_service.create_message(sample_message_data)
        
        result = message_service.update_message_content(created.id, "New content")
        
        assert result is not None
        assert result.content == "New content"
        assert result.tokens == sample_message_data.tokens  # Unchanged


class TestUpdateMessageFeedback:
    """Tests for update_message_feedback method."""
    
    def test_update_message_feedback_success(
        self,
        message_service: MessageService,
        sample_message_data: MessageCreate
    ):
        """Test updating message feedback."""
        created = message_service.create_message(sample_message_data)
        
        result = message_service.update_message_feedback(created.id, "positive")
        
        assert result is not None
        assert result.feedback == "positive"
    
    def test_update_message_feedback_not_found(self, message_service: MessageService):
        """Test updating feedback for non-existent message returns None."""
        result = message_service.update_message_feedback(uuid4(), "positive")
        
        assert result is None


class TestDeleteMessage:
    """Tests for delete_message method (soft delete)."""
    
    def test_delete_message_success(
        self,
        message_service: MessageService,
        sample_message_data: MessageCreate
    ):
        """Test successful soft delete."""
        created = message_service.create_message(sample_message_data)
        
        result = message_service.delete_message(created.id)
        
        assert result is True
        # Message should not be accessible
        assert message_service.get_message_by_id(created.id) is None
    
    def test_delete_message_not_found(self, message_service: MessageService):
        """Test deleting non-existent message returns False."""
        result = message_service.delete_message(uuid4())
        
        assert result is False


class TestPermanentlyDeleteMessage:
    """Tests for permanently_delete_message method (hard delete)."""
    
    def test_permanently_delete_message_success(
        self,
        message_service: MessageService,
        sample_message_data: MessageCreate
    ):
        """Test successful hard delete."""
        created = message_service.create_message(sample_message_data)
        
        result = message_service.permanently_delete_message(created.id)
        
        assert result is True
        assert message_service.get_message_by_id(created.id) is None
    
    def test_permanently_delete_message_not_found(self, message_service: MessageService):
        """Test permanently deleting non-existent message returns False."""
        result = message_service.permanently_delete_message(uuid4())
        
        assert result is False


class TestDeleteChatMessages:
    """Tests for delete_chat_messages method."""
    
    def test_delete_chat_messages_success(
        self,
        message_service: MessageService,
        test_chat,
        test_model
    ):
        """Test deleting all messages in a chat."""
        # Create multiple messages
        for i in range(3):
            message_data = MessageCreate(
                chat_id=test_chat.id,
                model_id=test_model.id,
                type="user",
                content=f"Message {i}"
            )
            message_service.create_message(message_data)
        
        count = message_service.delete_chat_messages(test_chat.id)
        
        assert count == 3
        assert len(message_service.get_active_messages(test_chat.id)) == 0


class TestCountChatMessages:
    """Tests for count_chat_messages method."""
    
    def test_count_chat_messages_empty(
        self,
        message_service: MessageService,
        test_chat
    ):
        """Test counting when no messages exist."""
        result = message_service.count_chat_messages(test_chat.id)
        
        assert result == 0
    
    def test_count_chat_messages_success(
        self,
        message_service: MessageService,
        test_chat,
        test_model
    ):
        """Test counting all messages."""
        for i in range(3):
            message_data = MessageCreate(
                chat_id=test_chat.id,
                model_id=test_model.id,
                type="user",
                content=f"Message {i}"
            )
            message_service.create_message(message_data)
        
        result = message_service.count_chat_messages(test_chat.id)
        
        assert result == 3
    
    def test_count_chat_messages_exclude_deleted(
        self,
        message_service: MessageService,
        test_chat,
        test_model
    ):
        """Test counting excludes deleted messages by default."""
        msg1_data = MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="user",
            content="Message 1"
        )
        msg1 = message_service.create_message(msg1_data)
        
        msg2_data = MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="user",
            content="Message 2"
        )
        message_service.create_message(msg2_data)
        
        message_service.delete_message(msg1.id)
        
        result = message_service.count_chat_messages(test_chat.id)
        
        assert result == 1


class TestCountActiveMessages:
    """Tests for count_active_messages method."""
    
    def test_count_active_messages(
        self,
        message_service: MessageService,
        test_chat,
        test_model
    ):
        """Test counting only active messages."""
        msg1_data = MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="user",
            content="Message 1"
        )
        msg1 = message_service.create_message(msg1_data)
        
        msg2_data = MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="user",
            content="Message 2"
        )
        message_service.create_message(msg2_data)
        
        message_service.delete_message(msg1.id)
        
        result = message_service.count_active_messages(test_chat.id)
        
        assert result == 1


class TestGetLatestMessage:
    """Tests for get_latest_message method."""
    
    def test_get_latest_message_success(
        self,
        message_service: MessageService,
        test_chat,
        test_model
    ):
        """Test getting the latest message."""
        msg1_data = MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="user",
            content="First message"
        )
        message_service.create_message(msg1_data)
        
        msg2_data = MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="user",
            content="Latest message"
        )
        msg2 = message_service.create_message(msg2_data)
        
        result = message_service.get_latest_message(test_chat.id)
        
        assert result is not None
        assert result.id == msg2.id
        assert result.content == "Latest message"
    
    def test_get_latest_message_empty(
        self,
        message_service: MessageService,
        test_chat
    ):
        """Test getting latest message when none exist."""
        result = message_service.get_latest_message(test_chat.id)
        
        assert result is None


class TestCalculateChatTokens:
    """Tests for calculate_chat_tokens method."""
    
    def test_calculate_chat_tokens(
        self,
        message_service: MessageService,
        test_chat,
        test_model
    ):
        """Test calculating total tokens."""
        msg1_data = MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="user",
            content="Message 1",
            tokens=10
        )
        message_service.create_message(msg1_data)
        
        msg2_data = MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="ai",
            content="Message 2",
            tokens=20
        )
        message_service.create_message(msg2_data)
        
        result = message_service.calculate_chat_tokens(test_chat.id)
        
        assert result == 30
    
    def test_calculate_chat_tokens_with_none_values(
        self,
        message_service: MessageService,
        test_chat,
        test_model
    ):
        """Test calculating tokens with some None values."""
        msg1_data = MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="user",
            content="Message 1",
            tokens=10
        )
        message_service.create_message(msg1_data)
        
        msg2_data = MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="ai",
            content="Message 2"
            # No tokens
        )
        message_service.create_message(msg2_data)
        
        result = message_service.calculate_chat_tokens(test_chat.id)
        
        assert result == 10


class TestCalculateChatCost:
    """Tests for calculate_chat_cost method."""
    
    def test_calculate_chat_cost(
        self,
        message_service: MessageService,
        test_chat,
        test_model
    ):
        """Test calculating total cost."""
        # test_model has price_per_million_tokens = 30.00
        # Create messages with 1000 tokens each
        for i in range(2):
            msg_data = MessageCreate(
                chat_id=test_chat.id,
                model_id=test_model.id,
                type="user",
                content=f"Message {i}",
                tokens=1000
            )
            message_service.create_message(msg_data)
        
        result = message_service.calculate_chat_cost(test_chat.id)
        
        # 2 messages * 1000 tokens * (30.00 / 1,000,000) = 0.06
        assert result == pytest.approx(0.06, rel=1e-6)
    
    def test_calculate_chat_cost_empty(
        self,
        message_service: MessageService,
        test_chat
    ):
        """Test calculating cost when no messages exist."""
        result = message_service.calculate_chat_cost(test_chat.id)
        
        assert result == 0.0


class TestMessageExists:
    """Tests for message_exists method."""
    
    def test_message_exists_true(
        self,
        message_service: MessageService,
        sample_message_data: MessageCreate
    ):
        """Test that existing message returns True."""
        created = message_service.create_message(sample_message_data)
        
        result = message_service.message_exists(created.id)
        
        assert result is True
    
    def test_message_exists_false(self, message_service: MessageService):
        """Test that non-existent message returns False."""
        result = message_service.message_exists(uuid4())
        
        assert result is False


class TestGetConversationSummary:
    """Tests for get_conversation_summary method."""
    
    def test_get_conversation_summary(
        self,
        message_service: MessageService,
        test_chat,
        test_model
    ):
        """Test getting conversation summary."""
        # Create user message
        user_msg = MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="user",
            content="User message",
            tokens=5
        )
        message_service.create_message(user_msg)
        
        # Create AI message
        ai_msg = MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="ai",
            content="AI message",
            tokens=10
        )
        message_service.create_message(ai_msg)
        
        result = message_service.get_conversation_summary(test_chat.id)
        
        assert result["total_messages"] == 2
        assert result["user_messages"] == 1
        assert result["ai_messages"] == 1
        assert result["system_messages"] == 0
        assert result["total_tokens"] == 15
        assert result["total_cost"] > 0
        assert result["latest_message_at"] is not None


class TestBulkDeleteMessages:
    """Tests for bulk_delete_messages method."""
    
    def test_bulk_delete_messages_success(
        self,
        message_service: MessageService,
        test_chat,
        test_model
    ):
        """Test bulk deleting multiple messages."""
        msg1_data = MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="user",
            content="Message 1"
        )
        msg1 = message_service.create_message(msg1_data)
        
        msg2_data = MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="user",
            content="Message 2"
        )
        msg2 = message_service.create_message(msg2_data)
        
        result = message_service.bulk_delete_messages([msg1.id, msg2.id])
        
        assert result["successful"] == 2
        assert result["failed"] == 0
        assert result["total"] == 2
    
    def test_bulk_delete_messages_partial_success(
        self,
        message_service: MessageService,
        test_chat,
        test_model
    ):
        """Test bulk delete with some failures."""
        msg1_data = MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="user",
            content="Message 1"
        )
        msg1 = message_service.create_message(msg1_data)
        
        non_existent_id = uuid4()
        
        result = message_service.bulk_delete_messages([msg1.id, non_existent_id])
        
        assert result["successful"] == 1
        assert result["failed"] == 1
        assert result["total"] == 2


class TestBulkPermanentlyDeleteMessages:
    """Tests for bulk_permanently_delete_messages method."""
    
    def test_bulk_permanently_delete_messages_success(
        self,
        message_service: MessageService,
        test_chat,
        test_model
    ):
        """Test bulk permanently deleting multiple messages."""
        msg1_data = MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="user",
            content="Message 1"
        )
        msg1 = message_service.create_message(msg1_data)
        
        msg2_data = MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="user",
            content="Message 2"
        )
        msg2 = message_service.create_message(msg2_data)
        
        result = message_service.bulk_permanently_delete_messages([msg1.id, msg2.id])
        
        assert result["successful"] == 2
        assert result["failed"] == 0
        assert result["total"] == 2
        
        # Verify messages are completely gone
        assert message_service.count_chat_messages(test_chat.id, include_deleted=True) == 0


class TestGetMessagesWithFeedback:
    """Tests for get_messages_with_feedback method."""
    
    def test_get_messages_with_feedback_all(
        self,
        message_service: MessageService,
        test_chat,
        test_model
    ):
        """Test getting all messages with feedback."""
        msg1_data = MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="user",
            content="Message 1"
        )
        msg1 = message_service.create_message(msg1_data)
        message_service.update_message_feedback(msg1.id, "positive")
        
        msg2_data = MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="ai",
            content="Message 2"
        )
        msg2 = message_service.create_message(msg2_data)
        message_service.update_message_feedback(msg2.id, "negative")
        
        # Message without feedback
        msg3_data = MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="user",
            content="Message 3"
        )
        message_service.create_message(msg3_data)
        
        result = message_service.get_messages_with_feedback(test_chat.id)
        
        assert len(result) == 2
    
    def test_get_messages_with_feedback_filtered(
        self,
        message_service: MessageService,
        test_chat,
        test_model
    ):
        """Test getting messages filtered by feedback type."""
        msg1_data = MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="user",
            content="Message 1"
        )
        msg1 = message_service.create_message(msg1_data)
        message_service.update_message_feedback(msg1.id, "positive")
        
        msg2_data = MessageCreate(
            chat_id=test_chat.id,
            model_id=test_model.id,
            type="ai",
            content="Message 2"
        )
        msg2 = message_service.create_message(msg2_data)
        message_service.update_message_feedback(msg2.id, "negative")
        
        positive_result = message_service.get_messages_with_feedback(
            test_chat.id,
            feedback_type="positive"
        )
        negative_result = message_service.get_messages_with_feedback(
            test_chat.id,
            feedback_type="negative"
        )
        
        assert len(positive_result) == 1
        assert len(negative_result) == 1
        assert positive_result[0].feedback == "positive"
        assert negative_result[0].feedback == "negative"
