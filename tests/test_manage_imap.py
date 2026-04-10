"""
Tests for manage_imap.EmailManager message selection.
"""

import pytest
from unittest.mock import Mock, patch

from manage_imap import EmailManager, RECENT_MESSAGES_LIMIT


class TestGetMessageChoice:
    """Tests for _get_message_choice method."""

    @pytest.fixture
    def manager(self):
        """Create an EmailManager instance."""
        return EmailManager()

    def test_select_first_message_few_posts(self, manager):
        """Test selecting message 0 when fewer than RECENT_MESSAGES_LIMIT posts exist."""
        posts = [f"msg_{i}" for i in range(5)]
        
        with patch.object(manager, '_get_int_input', return_value=0):
            result = manager._get_message_choice(posts)
        
        assert result == "msg_0"

    def test_select_second_message_few_posts(self, manager):
        """Test selecting message 1 when fewer than RECENT_MESSAGES_LIMIT posts exist."""
        posts = [f"msg_{i}" for i in range(5)]
        
        with patch.object(manager, '_get_int_input', return_value=1):
            result = manager._get_message_choice(posts)
        
        assert result == "msg_1"

    def test_select_last_message_few_posts(self, manager):
        """Test selecting the last message when fewer than RECENT_MESSAGES_LIMIT posts."""
        posts = [f"msg_{i}" for i in range(5)]
        
        with patch.object(manager, '_get_int_input', return_value=4):
            result = manager._get_message_choice(posts)
        
        assert result == "msg_4"

    def test_select_first_message_many_posts(self, manager):
        """Test selecting message 0 when more than RECENT_MESSAGES_LIMIT posts exist."""
        posts = [f"msg_{i}" for i in range(30)]
        
        with patch.object(manager, '_get_int_input', return_value=0):
            result = manager._get_message_choice(posts)
        
        # Should return the first of the last 15 messages (msg_15)
        assert result == "msg_15"

    def test_select_last_of_recent_messages(self, manager):
        """Test selecting the last visible message."""
        posts = [f"msg_{i}" for i in range(30)]
        
        # max_msg should be RECENT_MESSAGES_LIMIT - 1 = 14
        with patch.object(manager, '_get_int_input', return_value=14):
            result = manager._get_message_choice(posts)
        
        # Should return the last message (msg_29)
        assert result == "msg_29"

    def test_select_message_exactly_recent_limit(self, manager):
        """Test selecting messages when posts count equals RECENT_MESSAGES_LIMIT."""
        posts = [f"msg_{i}" for i in range(RECENT_MESSAGES_LIMIT)]
        
        with patch.object(manager, '_get_int_input', return_value=0):
            result = manager._get_message_choice(posts)
        
        assert result == "msg_0"
        
        with patch.object(manager, '_get_int_input', return_value=RECENT_MESSAGES_LIMIT - 1):
            result = manager._get_message_choice(posts)
        
        assert result == f"msg_{RECENT_MESSAGES_LIMIT - 1}"

    def test_user_cancels_selection(self, manager):
        """Test that user can cancel selection by typing 'q'."""
        posts = [f"msg_{i}" for i in range(5)]
        
        with patch.object(manager, '_get_int_input', return_value=None):
            result = manager._get_message_choice(posts)
        
        assert result is None
