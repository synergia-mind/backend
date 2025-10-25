import pytest
from uuid import uuid4
from sqlmodel import Session

from app.repositories.chat import ChatRepository
from app.models import ChatCreate, ChatUpdate


@pytest.fixture(name="repository")
def repository_fixture(session: Session):
    """
    Create a ChatRepository instance with the test session.
    """
    return ChatRepository(session)


@pytest.fixture(name="user_id")
def user_id_fixture():
    """
    Provide a sample user ID (Clerk-style string ID).
    """
    return f"user_{uuid4().hex[:24]}"


@pytest.fixture(name="other_user_id")
def other_user_id_fixture():
    """
    Provide a different user ID for testing authorization (Clerk-style string ID).
    """
    return f"user_{uuid4().hex[:24]}"


@pytest.fixture(name="sample_chat_data")
def sample_chat_data_fixture():
    """
    Provide sample chat creation data.
    """
    return ChatCreate(
        title="Test Chat",
        summary="This is a test chat"
    )


class TestChatRepositoryCreate:
    """Tests for the create method."""
    
    def test_create_chat_success(self, repository: ChatRepository, user_id, sample_chat_data: ChatCreate):
        """Test creating a new chat successfully."""
        chat = repository.create(user_id, sample_chat_data)
        
        assert chat.id is not None
        assert chat.user_id == user_id
        assert chat.title == "Test Chat"
        assert chat.summary == "This is a test chat"
        assert chat.is_deleted is False
        assert chat.created_at is not None
        assert chat.updated_at is not None
    
    def test_create_chat_without_optional_fields(self, repository: ChatRepository, user_id):
        """Test creating a chat without optional fields."""
        chat_data = ChatCreate()
        
        chat = repository.create(user_id, chat_data)
        
        assert chat.id is not None
        assert chat.user_id == user_id
        assert chat.title is None
        assert chat.summary is None
        assert chat.is_deleted is False
    
    def test_create_chat_with_only_title(self, repository: ChatRepository, user_id):
        """Test creating a chat with only title."""
        chat_data = ChatCreate(title="Only Title")
        
        chat = repository.create(user_id, chat_data)
        
        assert chat.title == "Only Title"
        assert chat.summary is None
    
    def test_create_multiple_chats_for_same_user(self, repository: ChatRepository, user_id):
        """Test creating multiple chats for the same user."""
        chat1_data = ChatCreate(title="Chat 1")
        chat2_data = ChatCreate(title="Chat 2")
        
        chat1 = repository.create(user_id, chat1_data)
        chat2 = repository.create(user_id, chat2_data)
        
        assert chat1.id != chat2.id
        assert chat1.user_id == chat2.user_id == user_id
    
    def test_create_chats_for_different_users(self, repository: ChatRepository, user_id, other_user_id):
        """Test creating chats for different users."""
        chat_data = ChatCreate(title="Same Title")
        
        chat1 = repository.create(user_id, chat_data)
        chat2 = repository.create(other_user_id, chat_data)
        
        assert chat1.user_id == user_id
        assert chat2.user_id == other_user_id
        assert chat1.id != chat2.id


class TestChatRepositoryGetById:
    """Tests for the get_by_id method."""
    
    def test_get_by_id_success(self, repository: ChatRepository, user_id, sample_chat_data: ChatCreate):
        """Test retrieving a chat by ID successfully."""
        created_chat = repository.create(user_id, sample_chat_data)
        
        retrieved_chat = repository.get_by_id(created_chat.id, user_id)
        
        assert retrieved_chat is not None
        assert retrieved_chat.id == created_chat.id
        assert retrieved_chat.title == created_chat.title
    
    def test_get_by_id_not_found(self, repository: ChatRepository, user_id):
        """Test retrieving a non-existent chat by ID."""
        non_existent_id = uuid4()
        
        chat = repository.get_by_id(non_existent_id, user_id)
        
        assert chat is None
    
    def test_get_by_id_wrong_user(self, repository: ChatRepository, user_id, other_user_id, sample_chat_data: ChatCreate):
        """Test that a user cannot retrieve another user's chat."""
        created_chat = repository.create(user_id, sample_chat_data)
        
        # Try to retrieve with different user_id
        chat = repository.get_by_id(created_chat.id, other_user_id)
        
        assert chat is None
    
    def test_get_by_id_deleted_chat(self, repository: ChatRepository, user_id, sample_chat_data: ChatCreate):
        """Test that soft-deleted chats are not retrieved."""
        created_chat = repository.create(user_id, sample_chat_data)
        repository.soft_delete(created_chat.id, user_id)
        
        chat = repository.get_by_id(created_chat.id, user_id)
        
        assert chat is None


class TestChatRepositoryGetAllByUser:
    """Tests for the get_all_by_user method."""
    
    def test_get_all_by_user_empty(self, repository: ChatRepository, user_id):
        """Test retrieving all chats for a user with no chats."""
        chats = repository.get_all_by_user(user_id)
        
        assert chats == []
    
    def test_get_all_by_user_with_chats(self, repository: ChatRepository, user_id):
        """Test retrieving all chats for a user."""
        chat1_data = ChatCreate(title="Chat 1")
        chat2_data = ChatCreate(title="Chat 2")
        
        repository.create(user_id, chat1_data)
        repository.create(user_id, chat2_data)
        
        chats = repository.get_all_by_user(user_id)
        
        assert len(chats) == 2
    
    def test_get_all_by_user_with_pagination(self, repository: ChatRepository, user_id):
        """Test pagination with skip and limit."""
        for i in range(5):
            chat_data = ChatCreate(title=f"Chat {i}")
            repository.create(user_id, chat_data)
        
        # Test skip
        chats = repository.get_all_by_user(user_id, skip=2)
        assert len(chats) == 3
        
        # Test limit
        chats = repository.get_all_by_user(user_id, limit=2)
        assert len(chats) == 2
        
        # Test skip and limit together
        chats = repository.get_all_by_user(user_id, skip=1, limit=2)
        assert len(chats) == 2
    
    def test_get_all_by_user_excludes_deleted(self, repository: ChatRepository, user_id):
        """Test that deleted chats are excluded by default."""
        chat1_data = ChatCreate(title="Active Chat")
        chat2_data = ChatCreate(title="Deleted Chat")
        
        chat1 = repository.create(user_id, chat1_data)
        chat2 = repository.create(user_id, chat2_data)
        
        # Soft delete chat2
        repository.soft_delete(chat2.id, user_id)
        
        chats = repository.get_all_by_user(user_id)
        
        assert len(chats) == 1
        assert chats[0].title == "Active Chat"
    
    def test_get_all_by_user_include_deleted(self, repository: ChatRepository, user_id):
        """Test retrieving all chats including deleted ones."""
        chat1_data = ChatCreate(title="Active Chat")
        chat2_data = ChatCreate(title="Deleted Chat")
        
        chat1 = repository.create(user_id, chat1_data)
        chat2 = repository.create(user_id, chat2_data)
        
        # Soft delete chat2
        repository.soft_delete(chat2.id, user_id)
        
        chats = repository.get_all_by_user(user_id, include_deleted=True)
        
        assert len(chats) == 2
    
    def test_get_all_by_user_ordered_by_updated_at(self, repository: ChatRepository, user_id):
        """Test that chats are ordered by updated_at descending (newest first)."""
        chat1 = repository.create(user_id, ChatCreate(title="First Chat"))
        chat2 = repository.create(user_id, ChatCreate(title="Second Chat"))
        chat3 = repository.create(user_id, ChatCreate(title="Third Chat"))
        
        chats = repository.get_all_by_user(user_id)
        
        # Most recently created/updated should be first
        assert chats[0].id == chat3.id
        assert chats[1].id == chat2.id
        assert chats[2].id == chat1.id
    
    def test_get_all_by_user_isolation(self, repository: ChatRepository, user_id, other_user_id):
        """Test that users only see their own chats."""
        user1_chat = ChatCreate(title="User 1 Chat")
        user2_chat = ChatCreate(title="User 2 Chat")
        
        repository.create(user_id, user1_chat)
        repository.create(other_user_id, user2_chat)
        
        user1_chats = repository.get_all_by_user(user_id)
        user2_chats = repository.get_all_by_user(other_user_id)
        
        assert len(user1_chats) == 1
        assert len(user2_chats) == 1
        assert user1_chats[0].title == "User 1 Chat"
        assert user2_chats[0].title == "User 2 Chat"


class TestChatRepositoryUpdate:
    """Tests for the update method."""
    
    def test_update_chat_success(self, repository: ChatRepository, user_id, sample_chat_data: ChatCreate):
        """Test updating a chat successfully."""
        created_chat = repository.create(user_id, sample_chat_data)
        original_updated_at = created_chat.updated_at
        
        update_data = ChatUpdate(
            title="Updated Title",
            summary="Updated summary"
        )
        
        updated_chat = repository.update(created_chat.id, user_id, update_data)
        
        assert updated_chat is not None
        assert updated_chat.title == "Updated Title"
        assert updated_chat.summary == "Updated summary"
        assert updated_chat.updated_at > original_updated_at
    
    def test_update_chat_not_found(self, repository: ChatRepository, user_id):
        """Test updating a non-existent chat."""
        non_existent_id = uuid4()
        update_data = ChatUpdate(title="New Title")
        
        result = repository.update(non_existent_id, user_id, update_data)
        
        assert result is None
    
    def test_update_chat_wrong_user(self, repository: ChatRepository, user_id, other_user_id, sample_chat_data: ChatCreate):
        """Test that a user cannot update another user's chat."""
        created_chat = repository.create(user_id, sample_chat_data)
        update_data = ChatUpdate(title="Hacked Title")
        
        result = repository.update(created_chat.id, other_user_id, update_data)
        
        assert result is None
        
        # Verify original chat is unchanged
        original_chat = repository.get_by_id(created_chat.id, user_id)
        assert original_chat is not None
        assert original_chat.title == "Test Chat"
    
    def test_update_partial_fields(self, repository: ChatRepository, user_id, sample_chat_data: ChatCreate):
        """Test updating only specific fields."""
        created_chat = repository.create(user_id, sample_chat_data)
        
        # Only update title
        update_data = ChatUpdate(title="Only Title Updated")
        updated_chat = repository.update(created_chat.id, user_id, update_data)
        
        assert updated_chat is not None
        assert updated_chat.title == "Only Title Updated"
        assert updated_chat.summary == created_chat.summary  # Unchanged
    
    def test_update_with_empty_data(self, repository: ChatRepository, user_id, sample_chat_data: ChatCreate):
        """Test update with no fields set (should only update updated_at)."""
        created_chat = repository.create(user_id, sample_chat_data)
        original_title = created_chat.title
        
        update_data = ChatUpdate()
        updated_chat = repository.update(created_chat.id, user_id, update_data)
        
        assert updated_chat is not None
        assert updated_chat.title == original_title
    
    def test_update_deleted_chat(self, repository: ChatRepository, user_id, sample_chat_data: ChatCreate):
        """Test that deleted chats cannot be updated."""
        created_chat = repository.create(user_id, sample_chat_data)
        repository.soft_delete(created_chat.id, user_id)
        
        update_data = ChatUpdate(title="Should Not Update")
        result = repository.update(created_chat.id, user_id, update_data)
        
        assert result is None


class TestChatRepositorySoftDelete:
    """Tests for the soft_delete method."""
    
    def test_soft_delete_success(self, repository: ChatRepository, user_id, sample_chat_data: ChatCreate):
        """Test soft deleting a chat successfully."""
        created_chat = repository.create(user_id, sample_chat_data)
        
        result = repository.soft_delete(created_chat.id, user_id)
        
        assert result is True
        
        # Verify it's marked as deleted
        chat = repository.get_by_id(created_chat.id, user_id)
        assert chat is None  # Should not be retrieved by default
    
    def test_soft_delete_not_found(self, repository: ChatRepository, user_id):
        """Test soft deleting a non-existent chat."""
        non_existent_id = uuid4()
        
        result = repository.soft_delete(non_existent_id, user_id)
        
        assert result is False
    
    def test_soft_delete_wrong_user(self, repository: ChatRepository, user_id, other_user_id, sample_chat_data: ChatCreate):
        """Test that a user cannot delete another user's chat."""
        created_chat = repository.create(user_id, sample_chat_data)
        
        result = repository.soft_delete(created_chat.id, other_user_id)
        
        assert result is False
        
        # Verify chat still exists
        chat = repository.get_by_id(created_chat.id, user_id)
        assert chat is not None
    
    def test_soft_delete_already_deleted(self, repository: ChatRepository, user_id, sample_chat_data: ChatCreate):
        """Test soft deleting an already deleted chat."""
        created_chat = repository.create(user_id, sample_chat_data)
        
        # First deletion
        result1 = repository.soft_delete(created_chat.id, user_id)
        assert result1 is True
        
        # Second deletion should fail (not found)
        result2 = repository.soft_delete(created_chat.id, user_id)
        assert result2 is False


class TestChatRepositoryHardDelete:
    """Tests for the hard_delete method."""
    
    def test_hard_delete_success(self, repository: ChatRepository, user_id, sample_chat_data: ChatCreate):
        """Test hard deleting a chat successfully."""
        created_chat = repository.create(user_id, sample_chat_data)
        
        result = repository.hard_delete(created_chat.id, user_id)
        
        assert result is True
        
        # Verify it's completely removed
        chats = repository.get_all_by_user(user_id, include_deleted=True)
        assert len(chats) == 0
    
    def test_hard_delete_not_found(self, repository: ChatRepository, user_id):
        """Test hard deleting a non-existent chat."""
        non_existent_id = uuid4()
        
        result = repository.hard_delete(non_existent_id, user_id)
        
        assert result is False
    
    def test_hard_delete_wrong_user(self, repository: ChatRepository, user_id, other_user_id, sample_chat_data: ChatCreate):
        """Test that a user cannot hard delete another user's chat."""
        created_chat = repository.create(user_id, sample_chat_data)
        
        result = repository.hard_delete(created_chat.id, other_user_id)
        
        assert result is False
        
        # Verify chat still exists
        chat = repository.get_by_id(created_chat.id, user_id)
        assert chat is not None
    
    def test_hard_delete_soft_deleted_chat(self, repository: ChatRepository, user_id, sample_chat_data: ChatCreate):
        """Test hard deleting a soft-deleted chat."""
        created_chat = repository.create(user_id, sample_chat_data)
        
        # First soft delete
        repository.soft_delete(created_chat.id, user_id)
        
        # Then hard delete
        result = repository.hard_delete(created_chat.id, user_id)
        
        assert result is True


class TestChatRepositoryRestore:
    """Tests for the restore method."""
    
    def test_restore_success(self, repository: ChatRepository, user_id, sample_chat_data: ChatCreate):
        """Test restoring a soft-deleted chat successfully."""
        created_chat = repository.create(user_id, sample_chat_data)
        repository.soft_delete(created_chat.id, user_id)
        
        restored_chat = repository.restore(created_chat.id, user_id)
        
        assert restored_chat is not None
        assert restored_chat.is_deleted is False
        
        # Verify it's accessible again
        chat = repository.get_by_id(created_chat.id, user_id)
        assert chat is not None
    
    def test_restore_not_found(self, repository: ChatRepository, user_id):
        """Test restoring a non-existent chat."""
        non_existent_id = uuid4()
        
        result = repository.restore(non_existent_id, user_id)
        
        assert result is None
    
    def test_restore_wrong_user(self, repository: ChatRepository, user_id, other_user_id, sample_chat_data: ChatCreate):
        """Test that a user cannot restore another user's chat."""
        created_chat = repository.create(user_id, sample_chat_data)
        repository.soft_delete(created_chat.id, user_id)
        
        result = repository.restore(created_chat.id, other_user_id)
        
        assert result is None
    
    def test_restore_non_deleted_chat(self, repository: ChatRepository, user_id, sample_chat_data: ChatCreate):
        """Test restoring a chat that isn't deleted."""
        created_chat = repository.create(user_id, sample_chat_data)
        
        result = repository.restore(created_chat.id, user_id)
        
        assert result is None
    
    def test_restore_updates_timestamp(self, repository: ChatRepository, user_id, sample_chat_data: ChatCreate):
        """Test that restoring updates the updated_at timestamp."""
        created_chat = repository.create(user_id, sample_chat_data)
        original_updated_at = created_chat.updated_at
        
        repository.soft_delete(created_chat.id, user_id)
        
        restored_chat = repository.restore(created_chat.id, user_id)
        
        assert restored_chat is not None
        assert restored_chat.updated_at >= original_updated_at


class TestChatRepositoryCountByUser:
    """Tests for the count_by_user method."""
    
    def test_count_by_user_empty(self, repository: ChatRepository, user_id):
        """Test counting chats for a user with no chats."""
        count = repository.count_by_user(user_id)
        
        assert count == 0
    
    def test_count_by_user_with_chats(self, repository: ChatRepository, user_id):
        """Test counting chats for a user."""
        for i in range(3):
            chat_data = ChatCreate(title=f"Chat {i}")
            repository.create(user_id, chat_data)
        
        count = repository.count_by_user(user_id)
        
        assert count == 3
    
    def test_count_by_user_excludes_deleted(self, repository: ChatRepository, user_id):
        """Test that deleted chats are excluded from count by default."""
        chat1 = repository.create(user_id, ChatCreate(title="Active"))
        chat2 = repository.create(user_id, ChatCreate(title="Deleted"))
        
        repository.soft_delete(chat2.id, user_id)
        
        count = repository.count_by_user(user_id)
        
        assert count == 1
    
    def test_count_by_user_include_deleted(self, repository: ChatRepository, user_id):
        """Test counting chats including deleted ones."""
        chat1 = repository.create(user_id, ChatCreate(title="Active"))
        chat2 = repository.create(user_id, ChatCreate(title="Deleted"))
        
        repository.soft_delete(chat2.id, user_id)
        
        count = repository.count_by_user(user_id, include_deleted=True)
        
        assert count == 2
    
    def test_count_by_user_isolation(self, repository: ChatRepository, user_id, other_user_id):
        """Test that count only includes user's own chats."""
        repository.create(user_id, ChatCreate(title="User 1 Chat"))
        repository.create(other_user_id, ChatCreate(title="User 2 Chat"))
        repository.create(other_user_id, ChatCreate(title="User 2 Chat 2"))
        
        count = repository.count_by_user(user_id)
        
        assert count == 1


class TestChatRepositoryIntegration:
    """Integration tests combining multiple repository operations."""
    
    def test_full_crud_cycle(self, repository: ChatRepository, user_id):
        """Test a complete CRUD cycle."""
        # Create
        chat_data = ChatCreate(title="Test Chat", summary="Test Summary")
        created_chat = repository.create(user_id, chat_data)
        assert created_chat.id is not None
        
        # Read
        retrieved_chat = repository.get_by_id(created_chat.id, user_id)
        assert retrieved_chat is not None
        assert retrieved_chat.title == "Test Chat"
        
        # Update
        update_data = ChatUpdate(title="Updated Chat")
        updated_chat = repository.update(created_chat.id, user_id, update_data)
        assert updated_chat is not None
        assert updated_chat.title == "Updated Chat"
        
        # Soft Delete
        delete_result = repository.soft_delete(created_chat.id, user_id)
        assert delete_result is True
        
        # Verify soft deletion
        deleted_chat = repository.get_by_id(created_chat.id, user_id)
        assert deleted_chat is None
        
        # Restore
        restored_chat = repository.restore(created_chat.id, user_id)
        assert restored_chat is not None
        assert restored_chat.is_deleted is False
        
        # Hard Delete
        hard_delete_result = repository.hard_delete(created_chat.id, user_id)
        assert hard_delete_result is True
        
        # Verify hard deletion
        all_chats = repository.get_all_by_user(user_id, include_deleted=True)
        assert len(all_chats) == 0
    
    def test_complex_multi_user_scenario(self, repository: ChatRepository, user_id, other_user_id):
        """Test a complex scenario with multiple users and operations."""
        # Create chats for both users
        user1_chat1 = repository.create(user_id, ChatCreate(title="User1 Chat1"))
        user1_chat2 = repository.create(user_id, ChatCreate(title="User1 Chat2"))
        user2_chat1 = repository.create(other_user_id, ChatCreate(title="User2 Chat1"))
        
        # Verify counts
        assert repository.count_by_user(user_id) == 2
        assert repository.count_by_user(other_user_id) == 1
        
        # Soft delete one chat for user1
        repository.soft_delete(user1_chat2.id, user_id)
        
        # Verify user1's active chats
        user1_chats = repository.get_all_by_user(user_id)
        assert len(user1_chats) == 1
        assert user1_chats[0].title == "User1 Chat1"
        
        # Verify user2 is unaffected
        assert repository.count_by_user(other_user_id) == 1
        
        # Update user1's remaining chat
        repository.update(user1_chat1.id, user_id, ChatUpdate(summary="Updated summary"))
        
        # Verify update
        updated = repository.get_by_id(user1_chat1.id, user_id)
        assert updated is not None
        assert updated.summary == "Updated summary"
        
        # Restore deleted chat
        restored = repository.restore(user1_chat2.id, user_id)
        assert restored is not None
        
        # Final count verification
        assert repository.count_by_user(user_id) == 2
        assert repository.count_by_user(other_user_id) == 1
    
    def test_soft_delete_restore_cycle(self, repository: ChatRepository, user_id):
        """Test multiple soft delete and restore cycles."""
        chat = repository.create(user_id, ChatCreate(title="Cycle Test"))
        
        for i in range(3):
            # Soft delete
            result = repository.soft_delete(chat.id, user_id)
            assert result is True
            assert repository.count_by_user(user_id) == 0
            
            # Restore
            restored = repository.restore(chat.id, user_id)
            assert restored is not None
            assert repository.count_by_user(user_id) == 1
