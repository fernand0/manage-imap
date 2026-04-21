"""
Tests for manage_imap.EmailManager message selection.
"""

import pytest
from unittest.mock import Mock, patch

from manage_imap import EmailManager, RECENT_MESSAGES_LIMIT
from socialModules.moduleFilterManager import EmailFilterRule, moduleFilterManager


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


class TestEmailManagerMoveMessage:
    """Tests for the move_message method in EmailManager."""

    @pytest.fixture
    def manager_with_mocks(self):
        """Fixture to set up EmailManager with necessary mocks."""
        manager = EmailManager()

        # Mock api_src (moduleImap)
        manager.api_src = Mock()
        manager.api_src.setPosts.return_value = None
        manager.api_src.getPosts.return_value = ["msg_1"]
        manager.api_src.getPostFrom.return_value = "sender@example.com"
        manager.api_src.getPostTitle.return_value = "Test Subject"
        manager.api_src.selectHeaderAuto.return_value = (
            "From", "dummy_text", "sender@example.com"
        )
        manager.api_src.getClient.return_value = Mock()
        manager.api_src.moveMails.return_value = "OK"

        # Mock rule_manager (moduleFilterManager)
        manager.rule_manager = Mock(spec=moduleFilterManager)
        manager.rule_manager.rules = {"always": [], "sometimes": []}
        manager.rule_manager.display_rules.return_value = None

        return manager

    def test_move_message_applies_suggested_rule(self, manager_with_mocks):
        """
        Test that move_message correctly identifies and applies a suggested rule
        when user confirms.
        """
        manager = manager_with_mocks
        
        # Add a matching rule to the manager
        matching_rule = EmailFilterRule(
            keyword="From", pattern="sender@example.com", folder="MatchedFolder"
        )
        manager.rule_manager.rules["always"].append(matching_rule)

        # Mock user inputs:
        # 1. Select message (0)
        # 2. Select rule to apply (0)
        # 3. Confirm applying the rule (True)
        with patch.object(manager, '_get_int_input', side_effect=[0, 0]), \
             patch.object(manager, '_confirm', return_value=True), \
             patch.object(manager, '_apply_rule_logic') as mock_apply_rule_logic, \
             patch.object(manager, '_extract_folder_suggestion') as mock_extract_folder_suggestion, \
             patch.object(manager.api_src, 'selectFolderN') as mock_select_folder_n:

            manager.move_message()

            # Assertions
            mock_apply_rule_logic.assert_called_once_with(matching_rule, interactive=True)
            
            # Ensure no further steps in the original move_message flow were executed
            mock_extract_folder_suggestion.assert_not_called()
            mock_select_folder_n.assert_not_called()

    def test_move_message_skips_suggested_rule_on_user_cancel(self, manager_with_mocks):
        """
        Test that move_message proceeds to folder suggestion if user cancels
        applying a suggested rule.
        """
        manager = manager_with_mocks

        # Add a matching rule
        matching_rule = EmailFilterRule(
            keyword="From", pattern="sender@example.com", folder="MatchedFolder"
        )
        manager.rule_manager.rules["always"].append(matching_rule)

        # Mock user inputs:
        # 1. Select message (0)
        # 2. Select rule to apply (0)
        # 3. Cancel applying the rule (False for first _confirm call)
        # 4. Confirm applying the newly created rule (True for second _confirm call)
        with patch.object(manager, '_get_int_input', side_effect=[0, 0, 0]), \
             patch.object(manager, '_confirm', side_effect=[False, True]), \
             patch.object(manager, '_apply_rule_logic') as mock_apply_rule_logic, \
             patch.object(manager, '_extract_folder_suggestion', return_value="sender") as mock_extract_folder_suggestion, \
             patch.object(manager.api_src, 'selectFolderN', return_value="SelectedFolder") as mock_select_folder_n:

            manager.move_message()

            # Assertions
            # _apply_rule_logic should NOT be called with the suggested rule
            mock_apply_rule_logic.assert_called_once()
            # It should be called with the rule created from the later flow
            assert mock_apply_rule_logic.call_args[0][0] == ('From', 'sender@example.com', 'SelectedFolder')
            
            # Ensure original flow continues
            mock_extract_folder_suggestion.assert_called_once_with('From', 'sender@example.com')
            mock_select_folder_n.assert_called_once_with(manager.api_src.getClient(), folderM="sender")

    def test_move_message_skips_suggested_rule_on_user_skip(self, manager_with_mocks):
        """
        Test that move_message proceeds to folder suggestion if user skips
        suggested rules.
        """
        manager = manager_with_mocks

        # Add a matching rule
        matching_rule = EmailFilterRule(
            keyword="From", pattern="sender@example.com", folder="MatchedFolder"
        )
        manager.rule_manager.rules["always"].append(matching_rule)

        # Mock user inputs:
        # 1. Select message (0)
        # 2. Skip rule application ('q' which is None)
        # 3. Choose rule type 'a' (0 for _get_int_input)
        with patch.object(manager, '_get_int_input', side_effect=[0, None, 0]), \
             patch.object(manager, '_confirm', return_value=True), \
             patch.object(manager, '_apply_rule_logic') as mock_apply_rule_logic, \
             patch.object(manager, '_extract_folder_suggestion', return_value="sender") as mock_extract_folder_suggestion, \
             patch.object(manager.api_src, 'selectFolderN', return_value="SelectedFolder") as mock_select_folder_n:

            manager.move_message()

            # Assertions
            mock_apply_rule_logic.assert_called_once()
            # It should be called with the rule created from the later flow
            assert mock_apply_rule_logic.call_args[0][0] == ('From', 'sender@example.com', 'SelectedFolder')
            
            # Ensure original flow continues
            mock_extract_folder_suggestion.assert_called_once_with('From', 'sender@example.com')
            mock_select_folder_n.assert_called_once_with(manager.api_src.getClient(), folderM="sender")

