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


class TestImapMoveMails:
    """Tests for moveMails method in moduleImap."""

    def test_move_mails_selects_channel_without_capitalize(self):
        """Test that moveMails selects the channel without mangling its name."""
        from socialModules.moduleImap import moduleImap

        imap = moduleImap()
        imap.channel = "INBOX"
        imap.user = "test@test.com"
        imap.server = "imap.test.com"

        mock_client = Mock()
        mock_client.select.return_value = ("OK", None)
        mock_client.copy.return_value = ("OK", None)
        mock_client.store.return_value = ("OK", None)

        imap.moveMails(mock_client, "1,2,3", "Archive")

        # Verify select was called with the exact channel name, not capitalized
        mock_client.select.assert_called_once_with("INBOX")
        assert mock_client.select.call_args[0][0] == "INBOX"
        # Ensure capitalize was NOT used
        assert mock_client.select.call_args[0][0] != "Inbox"

    def test_move_mails_preserves_folder_hierarchy(self):
        """Test that nested folder names like INBOX.sub.folder are preserved."""
        from socialModules.moduleImap import moduleImap

        imap = moduleImap()
        imap.channel = "INBOX.sub.folder"
        imap.user = "test@test.com"
        imap.server = "imap.test.com"

        mock_client = Mock()
        mock_client.select.return_value = ("OK", None)
        mock_client.copy.return_value = ("OK", None)
        mock_client.store.return_value = ("OK", None)

        imap.moveMails(mock_client, "1", "Dest")

        mock_client.select.assert_called_once_with("INBOX.sub.folder")


class TestSearchConstruction:
    """Tests for search criteria construction."""
    @pytest.fixture
    def manager(self):
        return EmailManager()

    def test_construct_standard_key_from(self, manager):
        assert manager._construct_search_criteria("From", "test@example.com") == ["FROM", "test@example.com"]

    def test_construct_standard_key_subject(self, manager):
        assert manager._construct_search_criteria("Subject", "Hello World") == ["SUBJECT", "Hello World"]

    def test_construct_standard_key_body(self, manager):
        assert manager._construct_search_criteria("BODY", "secret code") == ["BODY", "secret code"]

    def test_construct_header_custom(self, manager):
        assert manager._construct_search_criteria("X-Spam-Status", "Yes") == ["HEADER", "X-Spam-Status", "Yes"]

    def test_construct_header_list_id(self, manager):
        assert manager._construct_search_criteria("List-Id", "cordial.1.13.sparkpostmail.com") == ["HEADER", "List-Id", "cordial.1.13.sparkpostmail.com"]

    def test_construct_flag_unseen(self, manager):
        assert manager._construct_search_criteria("UNSEEN", "") == ["UNSEEN"]

    def test_construct_case_insensitivity(self, manager):
        assert manager._construct_search_criteria("from", "test") == ["FROM", "test"]
