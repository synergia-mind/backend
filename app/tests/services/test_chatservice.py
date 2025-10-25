import pytest
from uuid import uuid4, UUID
from sqlmodel import Session

from app.services.chat import ChatService
from app.models import ChatCreate, ChatUpdate


@pytest.fixture
def chat_service(session: Session):
    """Create a ChatService instance with test session."""
    return ChatService(session)


@pytest.fixture
def user_id() -> str:
    """Sample user ID (Clerk-style string ID)."""
    return f"user_{uuid4().hex[:24]}"


@pytest.fixture
def another_user_id() -> str:
    """Another sample user ID (Clerk-style string ID)."""
    return f"user_{uuid4().hex[:24]}"


@pytest.fixture
def sample_chat_data():
    """Sample chat creation data."""
    return ChatCreate(
        title="My Test Chat",
        summary="This is a test chat summary"
    )


@pytest.fixture
def another_chat_data():
    """Another sample chat creation data."""
    return ChatCreate(
        title="Another Chat",
        summary="Another summary"
    )


class TestCreateChat:
    """Tests for create_chat method."""
    
    def test_create_chat_success(
        self,
        chat_service: ChatService,
        user_id: str,
        sample_chat_data: ChatCreate
    ):
        """Test successful chat creation."""
        result = chat_service.create_chat(user_id, sample_chat_data)
        
        assert result.title == sample_chat_data.title
        assert result.summary == sample_chat_data.summary
        assert result.user_id == user_id
        assert result.is_deleted is False
        assert result.id is not None
        assert result.created_at is not None
        assert result.updated_at is not None
    
    def test_create_chat_minimal_data(self, chat_service: ChatService, user_id: str):
        """Test creating chat with minimal data (no title/summary)."""
        chat_data = ChatCreate()
        result = chat_service.create_chat(user_id, chat_data)
        
        assert result.user_id == user_id
        assert result.is_deleted is False
        assert result.title is None
        assert result.summary is None
    
    def test_create_chat_with_title_only(self, chat_service: ChatService, user_id: str):
        """Test creating chat with only title."""
        chat_data = ChatCreate(title="Only Title")
        result = chat_service.create_chat(user_id, chat_data)
        
        assert result.title == "Only Title"
        assert result.summary is None


class TestGetOrCreateChat:
    """Tests for get_or_create_chat method."""
    
    def test_get_existing_chat(
        self,
        chat_service: ChatService,
        user_id: str,
        sample_chat_data: ChatCreate
    ):
        """Test getting an existing chat."""
        created = chat_service.create_chat(user_id, sample_chat_data)
        
        result = chat_service.get_or_create_chat(user_id, chat_id=created.id)
        
        assert result.id == created.id
        assert result.title == created.title
    
    def test_create_new_chat_when_no_id(
        self,
        chat_service: ChatService,
        user_id: str
    ):
        """Test creating new chat when chat_id is None."""
        result = chat_service.get_or_create_chat(user_id, chat_id=None)
        
        assert result.id is not None
        assert result.title == "New Chat"
        assert result.user_id == user_id
    
    def test_create_new_chat_with_auto_title(
        self,
        chat_service: ChatService,
        user_id: str
    ):
        """Test creating new chat with custom auto_title."""
        result = chat_service.get_or_create_chat(
            user_id,
            chat_id=None,
            auto_title="Custom Auto Title"
        )
        
        assert result.title == "Custom Auto Title"
    
    def test_get_or_create_chat_nonexistent_id(
        self,
        chat_service: ChatService,
        user_id: str
    ):
        """Test error when trying to get non-existent chat."""
        non_existent_id = uuid4()
        
        with pytest.raises(ValueError, match="does not exist or you don't have access"):
            chat_service.get_or_create_chat(user_id, chat_id=non_existent_id)
    
    def test_get_or_create_chat_wrong_user(
        self,
        chat_service: ChatService,
        user_id: str,
        another_user_id: str,
        sample_chat_data: ChatCreate
    ):
        """Test error when user tries to access another user's chat."""
        created = chat_service.create_chat(user_id, sample_chat_data)
        
        with pytest.raises(ValueError, match="does not exist or you don't have access"):
            chat_service.get_or_create_chat(another_user_id, chat_id=created.id)


class TestGetChatById:
    """Tests for get_chat_by_id method."""
    
    def test_get_chat_by_id_success(
        self,
        chat_service: ChatService,
        user_id: str,
        sample_chat_data: ChatCreate
    ):
        """Test successful retrieval by ID."""
        created = chat_service.create_chat(user_id, sample_chat_data)
        
        result = chat_service.get_chat_by_id(created.id, user_id)
        
        assert result is not None
        assert result.id == created.id
        assert result.title == created.title
    
    def test_get_chat_by_id_not_found(self, chat_service: ChatService, user_id: str):
        """Test retrieval with non-existent ID returns None."""
        result = chat_service.get_chat_by_id(uuid4(), user_id)
        
        assert result is None
    
    def test_get_chat_by_id_wrong_user(
        self,
        chat_service: ChatService,
        user_id: str,
        another_user_id: str,
        sample_chat_data: ChatCreate
    ):
        """Test that user cannot access another user's chat."""
        created = chat_service.create_chat(user_id, sample_chat_data)
        
        result = chat_service.get_chat_by_id(created.id, another_user_id)
        
        assert result is None
    
    def test_get_chat_by_id_deleted_chat(
        self,
        chat_service: ChatService,
        user_id: str,
        sample_chat_data: ChatCreate
    ):
        """Test that deleted chats are not returned."""
        created = chat_service.create_chat(user_id, sample_chat_data)
        chat_service.delete_chat(created.id, user_id)
        
        result = chat_service.get_chat_by_id(created.id, user_id)
        
        assert result is None


class TestGetAllUserChats:
    """Tests for get_all_user_chats method."""
    
    def test_get_all_user_chats_empty(self, chat_service: ChatService, user_id: str):
        """Test getting chats when none exist."""
        result = chat_service.get_all_user_chats(user_id)
        
        assert result == []
    
    def test_get_all_user_chats_success(
        self,
        chat_service: ChatService,
        user_id: str,
        sample_chat_data: ChatCreate,
        another_chat_data: ChatCreate
    ):
        """Test getting all chats for a user."""
        chat_service.create_chat(user_id, sample_chat_data)
        chat_service.create_chat(user_id, another_chat_data)
        
        result = chat_service.get_all_user_chats(user_id)
        
        assert len(result) == 2
    
    def test_get_all_user_chats_pagination(
        self,
        chat_service: ChatService,
        user_id: str,
        sample_chat_data: ChatCreate,
        another_chat_data: ChatCreate
    ):
        """Test pagination."""
        chat_service.create_chat(user_id, sample_chat_data)
        chat_service.create_chat(user_id, another_chat_data)
        
        result = chat_service.get_all_user_chats(user_id, skip=0, limit=1)
        assert len(result) == 1
        
        result = chat_service.get_all_user_chats(user_id, skip=1, limit=1)
        assert len(result) == 1
    
    def test_get_all_user_chats_excludes_deleted(
        self,
        chat_service: ChatService,
        user_id: str,
        sample_chat_data: ChatCreate,
        another_chat_data: ChatCreate
    ):
        """Test that deleted chats are excluded by default."""
        chat1 = chat_service.create_chat(user_id, sample_chat_data)
        chat_service.create_chat(user_id, another_chat_data)
        
        # Delete one chat
        chat_service.delete_chat(chat1.id, user_id)
        
        result = chat_service.get_all_user_chats(user_id)
        
        assert len(result) == 1
    
    def test_get_all_user_chats_include_deleted(
        self,
        chat_service: ChatService,
        user_id: str,
        sample_chat_data: ChatCreate,
        another_chat_data: ChatCreate
    ):
        """Test including deleted chats."""
        chat1 = chat_service.create_chat(user_id, sample_chat_data)
        chat_service.create_chat(user_id, another_chat_data)
        
        # Delete one chat
        chat_service.delete_chat(chat1.id, user_id)
        
        result = chat_service.get_all_user_chats(user_id, include_deleted=True)
        
        assert len(result) == 2
    
    def test_get_all_user_chats_isolation(
        self,
        chat_service: ChatService,
        user_id: str,
        another_user_id: str,
        sample_chat_data: ChatCreate
    ):
        """Test that users only see their own chats."""
        chat_service.create_chat(user_id, sample_chat_data)
        chat_service.create_chat(another_user_id, sample_chat_data)
        
        result = chat_service.get_all_user_chats(user_id)
        
        assert len(result) == 1
        assert result[0].user_id == user_id


class TestGetActiveChats:
    """Tests for get_active_chats method."""
    
    def test_get_active_chats(
        self,
        chat_service: ChatService,
        user_id: str,
        sample_chat_data: ChatCreate,
        another_chat_data: ChatCreate
    ):
        """Test getting only active chats."""
        chat1 = chat_service.create_chat(user_id, sample_chat_data)
        chat_service.create_chat(user_id, another_chat_data)
        
        # Delete one chat
        chat_service.delete_chat(chat1.id, user_id)
        
        result = chat_service.get_active_chats(user_id)
        
        assert len(result) == 1
        assert all(not chat.is_deleted for chat in result)


class TestUpdateChat:
    """Tests for update_chat method."""
    
    def test_update_chat_success(
        self,
        chat_service: ChatService,
        user_id: str,
        sample_chat_data: ChatCreate
    ):
        """Test successful chat update."""
        created = chat_service.create_chat(user_id, sample_chat_data)
        
        update_data = ChatUpdate(
            title="Updated Title",
            summary="Updated Summary"
        )
        result = chat_service.update_chat(created.id, user_id, update_data)
        
        assert result is not None
        assert result.title == "Updated Title"
        assert result.summary == "Updated Summary"
    
    def test_update_chat_partial(
        self,
        chat_service: ChatService,
        user_id: str,
        sample_chat_data: ChatCreate
    ):
        """Test partial update (only title)."""
        created = chat_service.create_chat(user_id, sample_chat_data)
        
        update_data = ChatUpdate(title="Only Title Updated")
        result = chat_service.update_chat(created.id, user_id, update_data)
        
        assert result is not None
        assert result.title == "Only Title Updated"
        assert result.summary == sample_chat_data.summary  # Unchanged
    
    def test_update_chat_not_found(
        self,
        chat_service: ChatService,
        user_id: str
    ):
        """Test updating non-existent chat returns None."""
        update_data = ChatUpdate(title="New Title")
        result = chat_service.update_chat(uuid4(), user_id, update_data)
        
        assert result is None
    
    def test_update_chat_wrong_user(
        self,
        chat_service: ChatService,
        user_id: str,
        another_user_id: str,
        sample_chat_data: ChatCreate
    ):
        """Test that user cannot update another user's chat."""
        created = chat_service.create_chat(user_id, sample_chat_data)
        
        update_data = ChatUpdate(title="Hacked Title")
        result = chat_service.update_chat(created.id, another_user_id, update_data)
        
        assert result is None


class TestDeleteChat:
    """Tests for delete_chat method (soft delete)."""
    
    def test_delete_chat_success(
        self,
        chat_service: ChatService,
        user_id: str,
        sample_chat_data: ChatCreate
    ):
        """Test successful soft delete."""
        created = chat_service.create_chat(user_id, sample_chat_data)
        
        result = chat_service.delete_chat(created.id, user_id)
        
        assert result is True
        # Chat should not be accessible via normal get
        assert chat_service.get_chat_by_id(created.id, user_id) is None
    
    def test_delete_chat_not_found(self, chat_service: ChatService, user_id: str):
        """Test deleting non-existent chat returns False."""
        result = chat_service.delete_chat(uuid4(), user_id)
        
        assert result is False
    
    def test_delete_chat_wrong_user(
        self,
        chat_service: ChatService,
        user_id: str,
        another_user_id: str,
        sample_chat_data: ChatCreate
    ):
        """Test that user cannot delete another user's chat."""
        created = chat_service.create_chat(user_id, sample_chat_data)
        
        result = chat_service.delete_chat(created.id, another_user_id)
        
        assert result is False


class TestPermanentlyDeleteChat:
    """Tests for permanently_delete_chat method (hard delete)."""
    
    def test_permanently_delete_chat_success(
        self,
        chat_service: ChatService,
        user_id: str,
        sample_chat_data: ChatCreate
    ):
        """Test successful hard delete."""
        created = chat_service.create_chat(user_id, sample_chat_data)
        
        result = chat_service.permanently_delete_chat(created.id, user_id)
        
        assert result is True
        # Chat should not exist at all
        assert chat_service.get_chat_by_id(created.id, user_id) is None
    
    def test_permanently_delete_chat_not_found(
        self,
        chat_service: ChatService,
        user_id: str
    ):
        """Test permanently deleting non-existent chat returns False."""
        result = chat_service.permanently_delete_chat(uuid4(), user_id)
        
        assert result is False


class TestRestoreChat:
    """Tests for restore_chat method."""
    
    def test_restore_chat_success(
        self,
        chat_service: ChatService,
        user_id: str,
        sample_chat_data: ChatCreate
    ):
        """Test successful chat restoration."""
        created = chat_service.create_chat(user_id, sample_chat_data)
        
        # Soft delete
        chat_service.delete_chat(created.id, user_id)
        
        # Restore
        result = chat_service.restore_chat(created.id, user_id)
        
        assert result is not None
        assert result.is_deleted is False
        assert chat_service.get_chat_by_id(created.id, user_id) is not None
    
    def test_restore_chat_not_found(self, chat_service: ChatService, user_id: str):
        """Test restoring non-existent chat returns None."""
        result = chat_service.restore_chat(uuid4(), user_id)
        
        assert result is None
    
    def test_restore_active_chat(
        self,
        chat_service: ChatService,
        user_id: str,
        sample_chat_data: ChatCreate
    ):
        """Test restoring already active chat returns None."""
        created = chat_service.create_chat(user_id, sample_chat_data)
        
        result = chat_service.restore_chat(created.id, user_id)
        
        assert result is None


class TestCountUserChats:
    """Tests for count_user_chats method."""
    
    def test_count_user_chats_empty(self, chat_service: ChatService, user_id: str):
        """Test counting when no chats exist."""
        result = chat_service.count_user_chats(user_id)
        
        assert result == 0
    
    def test_count_user_chats_success(
        self,
        chat_service: ChatService,
        user_id: str,
        sample_chat_data: ChatCreate,
        another_chat_data: ChatCreate
    ):
        """Test counting all chats."""
        chat_service.create_chat(user_id, sample_chat_data)
        chat_service.create_chat(user_id, another_chat_data)
        
        result = chat_service.count_user_chats(user_id)
        
        assert result == 2
    
    def test_count_user_chats_exclude_deleted(
        self,
        chat_service: ChatService,
        user_id: str,
        sample_chat_data: ChatCreate,
        another_chat_data: ChatCreate
    ):
        """Test counting excludes deleted chats by default."""
        chat1 = chat_service.create_chat(user_id, sample_chat_data)
        chat_service.create_chat(user_id, another_chat_data)
        
        chat_service.delete_chat(chat1.id, user_id)
        
        result = chat_service.count_user_chats(user_id)
        
        assert result == 1
    
    def test_count_user_chats_include_deleted(
        self,
        chat_service: ChatService,
        user_id: str,
        sample_chat_data: ChatCreate,
        another_chat_data: ChatCreate
    ):
        """Test counting with deleted chats included."""
        chat1 = chat_service.create_chat(user_id, sample_chat_data)
        chat_service.create_chat(user_id, another_chat_data)
        
        chat_service.delete_chat(chat1.id, user_id)
        
        result = chat_service.count_user_chats(user_id, include_deleted=True)
        
        assert result == 2


class TestCountActiveChats:
    """Tests for count_active_chats method."""
    
    def test_count_active_chats(
        self,
        chat_service: ChatService,
        user_id: str,
        sample_chat_data: ChatCreate,
        another_chat_data: ChatCreate
    ):
        """Test counting only active chats."""
        chat1 = chat_service.create_chat(user_id, sample_chat_data)
        chat_service.create_chat(user_id, another_chat_data)
        
        chat_service.delete_chat(chat1.id, user_id)
        
        result = chat_service.count_active_chats(user_id)
        
        assert result == 1


class TestCountDeletedChats:
    """Tests for count_deleted_chats method."""
    
    def test_count_deleted_chats(
        self,
        chat_service: ChatService,
        user_id: str,
        sample_chat_data: ChatCreate,
        another_chat_data: ChatCreate
    ):
        """Test counting only deleted chats."""
        chat1 = chat_service.create_chat(user_id, sample_chat_data)
        chat2 = chat_service.create_chat(user_id, another_chat_data)
        
        chat_service.delete_chat(chat1.id, user_id)
        chat_service.delete_chat(chat2.id, user_id)
        
        result = chat_service.count_deleted_chats(user_id)
        
        assert result == 2


class TestGetDeletedChats:
    """Tests for get_deleted_chats method."""
    
    def test_get_deleted_chats(
        self,
        chat_service: ChatService,
        user_id: str,
        sample_chat_data: ChatCreate,
        another_chat_data: ChatCreate
    ):
        """Test getting only deleted chats."""
        chat1 = chat_service.create_chat(user_id, sample_chat_data)
        chat2 = chat_service.create_chat(user_id, another_chat_data)
        
        chat_service.delete_chat(chat1.id, user_id)
        
        result = chat_service.get_deleted_chats(user_id)
        
        assert len(result) == 1
        assert result[0].id == chat1.id
        assert result[0].is_deleted is True


class TestUpdateChatTitle:
    """Tests for update_chat_title method."""
    
    def test_update_chat_title_success(
        self,
        chat_service: ChatService,
        user_id: str,
        sample_chat_data: ChatCreate
    ):
        """Test updating only the title."""
        created = chat_service.create_chat(user_id, sample_chat_data)
        
        result = chat_service.update_chat_title(created.id, user_id, "New Title")
        
        assert result is not None
        assert result.title == "New Title"
        assert result.summary == sample_chat_data.summary  # Unchanged


class TestUpdateChatSummary:
    """Tests for update_chat_summary method."""
    
    def test_update_chat_summary_success(
        self,
        chat_service: ChatService,
        user_id: str,
        sample_chat_data: ChatCreate
    ):
        """Test updating only the summary."""
        created = chat_service.create_chat(user_id, sample_chat_data)
        
        result = chat_service.update_chat_summary(created.id, user_id, "New Summary")
        
        assert result is not None
        assert result.summary == "New Summary"
        assert result.title == sample_chat_data.title  # Unchanged


class TestChatExists:
    """Tests for chat_exists method."""
    
    def test_chat_exists_true(
        self,
        chat_service: ChatService,
        user_id: str,
        sample_chat_data: ChatCreate
    ):
        """Test that existing chat returns True."""
        created = chat_service.create_chat(user_id, sample_chat_data)
        
        result = chat_service.chat_exists(created.id, user_id)
        
        assert result is True
    
    def test_chat_exists_false(self, chat_service: ChatService, user_id: str):
        """Test that non-existent chat returns False."""
        result = chat_service.chat_exists(uuid4(), user_id)
        
        assert result is False
    
    def test_chat_exists_wrong_user(
        self,
        chat_service: ChatService,
        user_id: str,
        another_user_id: str,
        sample_chat_data: ChatCreate
    ):
        """Test that chat exists returns False for wrong user."""
        created = chat_service.create_chat(user_id, sample_chat_data)
        
        result = chat_service.chat_exists(created.id, another_user_id)
        
        assert result is False


class TestBulkDeleteChats:
    """Tests for bulk_delete_chats method."""
    
    def test_bulk_delete_chats_success(
        self,
        chat_service: ChatService,
        user_id: str,
        sample_chat_data: ChatCreate,
        another_chat_data: ChatCreate
    ):
        """Test bulk deleting multiple chats."""
        chat1 = chat_service.create_chat(user_id, sample_chat_data)
        chat2 = chat_service.create_chat(user_id, another_chat_data)
        
        result = chat_service.bulk_delete_chats([chat1.id, chat2.id], user_id)
        
        assert result["successful"] == 2
        assert result["failed"] == 0
        assert result["total"] == 2
    
    def test_bulk_delete_chats_partial_success(
        self,
        chat_service: ChatService,
        user_id: str,
        sample_chat_data: ChatCreate
    ):
        """Test bulk delete with some failures."""
        chat1 = chat_service.create_chat(user_id, sample_chat_data)
        non_existent_id = uuid4()
        
        result = chat_service.bulk_delete_chats([chat1.id, non_existent_id], user_id)
        
        assert result["successful"] == 1
        assert result["failed"] == 1
        assert result["total"] == 2


class TestBulkRestoreChats:
    """Tests for bulk_restore_chats method."""
    
    def test_bulk_restore_chats_success(
        self,
        chat_service: ChatService,
        user_id: str,
        sample_chat_data: ChatCreate,
        another_chat_data: ChatCreate
    ):
        """Test bulk restoring multiple chats."""
        chat1 = chat_service.create_chat(user_id, sample_chat_data)
        chat2 = chat_service.create_chat(user_id, another_chat_data)
        
        # Delete both
        chat_service.delete_chat(chat1.id, user_id)
        chat_service.delete_chat(chat2.id, user_id)
        
        # Restore both
        result = chat_service.bulk_restore_chats([chat1.id, chat2.id], user_id)
        
        assert result["successful"] == 2
        assert result["failed"] == 0
        assert result["total"] == 2


class TestBulkPermanentlyDeleteChats:
    """Tests for bulk_permanently_delete_chats method."""
    
    def test_bulk_permanently_delete_chats_success(
        self,
        chat_service: ChatService,
        user_id: str,
        sample_chat_data: ChatCreate,
        another_chat_data: ChatCreate
    ):
        """Test bulk permanently deleting multiple chats."""
        chat1 = chat_service.create_chat(user_id, sample_chat_data)
        chat2 = chat_service.create_chat(user_id, another_chat_data)
        
        result = chat_service.bulk_permanently_delete_chats([chat1.id, chat2.id], user_id)
        
        assert result["successful"] == 2
        assert result["failed"] == 0
        assert result["total"] == 2
        
        # Verify chats are completely gone
        assert chat_service.count_user_chats(user_id, include_deleted=True) == 0
