"""
Tests for the EmailRuleManager class.
"""

import json
import os
import tempfile
import pytest

from rule_manager import EmailRuleManager, EmailRule


class TestEmailRule:
    """Tests for the EmailRule dataclass."""

    def test_create_rule(self):
        """Test creating a rule with valid parameters."""
        rule = EmailRule(keyword="From", pattern="example@test.com", folder="Inbox")
        assert rule.keyword == "From"
        assert rule.pattern == "example@test.com"
        assert rule.folder == "Inbox"

    def test_from_tuple(self):
        """Test creating a rule from a tuple format."""
        rule_tuple = ("From", "notifications@github.com", "GitHub")
        rule = EmailRule.from_tuple(rule_tuple)
        assert rule.keyword == "From"
        assert rule.pattern == "notifications@github.com"
        assert rule.folder == "GitHub"

    def test_to_tuple(self):
        """Test converting a rule to tuple format."""
        rule = EmailRule(keyword="Subject", pattern="Invoice", folder="Billing")
        assert rule.to_tuple() == ("Subject", "Invoice", "Billing")

    def test_matches_case_insensitive(self):
        """Test that rule matching is case-insensitive."""
        rule = EmailRule(keyword="From", pattern="test@example.com", folder="Test")
        assert rule.matches("TEST@EXAMPLE.COM")
        assert rule.matches("test@example.com")
        assert rule.matches("Test@Example.Com")

    def test_matches_partial(self):
        """Test that rule matching works with partial matches."""
        rule = EmailRule(keyword="From", pattern="github", folder="Dev")
        assert rule.matches("notifications@github.com")
        assert rule.matches("github-support")
        assert not rule.matches("gitlab.com")

    def test_equality(self):
        """Test rule equality comparison."""
        rule1 = EmailRule(keyword="From", pattern="test@test.com", folder="Inbox")
        rule2 = EmailRule(keyword="From", pattern="test@test.com", folder="Inbox")
        rule3 = EmailRule(keyword="From", pattern="other@test.com", folder="Inbox")
        
        assert rule1 == rule2
        assert rule1 != rule3


class TestEmailRuleManager:
    """Tests for the EmailRuleManager class."""

    @pytest.fixture
    def temp_rules_file(self):
        """Create a temporary rules file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        yield temp_path
        # Cleanup
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    @pytest.fixture
    def rule_manager(self, temp_rules_file):
        """Create a rule manager instance with a temporary file."""
        return EmailRuleManager(temp_rules_file)

    def test_init_empty_file(self, temp_rules_file):
        """Test initialization with non-existent file."""
        manager = EmailRuleManager(temp_rules_file)
        assert manager.rules == {"always": [], "sometimes": []}

    def test_add_rule(self, rule_manager):
        """Test adding a rule."""
        rule = EmailRule(keyword="From", pattern="test@test.com", folder="Inbox")
        rule_manager.add_rule(rule, "always")
        
        assert len(rule_manager.rules["always"]) == 1
        assert rule_manager.rules["always"][0] == rule

    def test_add_rule_from_tuple(self, rule_manager):
        """Test adding a rule from tuple format."""
        rule_tuple = ("Subject", "Invoice", "Billing")
        rule_manager.add_rule(rule_tuple, "sometimes")
        
        assert len(rule_manager.rules["sometimes"]) == 1
        assert rule_manager.rules["sometimes"][0].keyword == "Subject"

    def test_add_rule_prevents_duplicates(self, rule_manager):
        """Test that duplicate rules are not added."""
        rule = EmailRule(keyword="From", pattern="test@test.com", folder="Inbox")
        rule_manager.add_rule(rule, "always")
        rule_manager.add_rule(rule, "always")  # Try to add again
        
        assert len(rule_manager.rules["always"]) == 1

    def test_remove_rule(self, rule_manager):
        """Test removing a rule."""
        rule = EmailRule(keyword="From", pattern="test@test.com", folder="Inbox")
        rule_manager.add_rule(rule, "always")
        
        result = rule_manager.remove_rule(rule, "always")
        assert result is True
        assert len(rule_manager.rules["always"]) == 0

    def test_remove_nonexistent_rule(self, rule_manager):
        """Test removing a rule that doesn't exist."""
        rule = EmailRule(keyword="From", pattern="test@test.com", folder="Inbox")
        
        result = rule_manager.remove_rule(rule, "default")
        assert result is False

    def test_save_and_load_rules(self, temp_rules_file):
        """Test saving and loading rules."""
        manager = EmailRuleManager(temp_rules_file)
        
        # Add some rules
        manager.add_rule(EmailRule("From", "test@test.com", "Inbox"), "always")
        manager.add_rule(EmailRule("Subject", "Invoice", "Billing"), "sometimes")
        
        # Save
        manager.save_rules()
        
        # Verify file exists and is valid JSON
        assert os.path.exists(temp_rules_file)
        with open(temp_rules_file, 'r') as f:
            data = json.load(f)
        
        assert data["version"] == EmailRuleManager.RULES_VERSION
        assert len(data["always"]) == 1
        assert len(data["sometimes"]) == 1

    def test_load_json_rules(self, temp_rules_file):
        """Test loading rules from JSON file."""
        # Create a JSON file manually
        data = {
            "version": "1.0",
            "always": [
                {"keyword": "From", "pattern": "test@test.com", "folder": "Inbox"}
            ],
            "sometimes": [
                {"keyword": "Subject", "pattern": "Sale", "folder": "Promotions"}
            ]
        }
        with open(temp_rules_file, 'w') as f:
            json.dump(data, f)
        
        manager = EmailRuleManager(temp_rules_file)
        
        assert len(manager.rules["always"]) == 1
        assert len(manager.rules["sometimes"]) == 1
        assert manager.rules["always"][0].pattern == "test@test.com"

    def test_invalid_json_raises_error(self, temp_rules_file):
        """Test that invalid JSON raises an error."""
        with open(temp_rules_file, 'w') as f:
            f.write("This is not valid JSON")
        
        with pytest.raises((json.JSONDecodeError, ValueError)):
            EmailRuleManager(temp_rules_file)

    def test_get_rules(self, rule_manager):
        """Test getting rules with optional filter."""
        rule1 = EmailRule("From", "test1@test.com", "Inbox")
        rule2 = EmailRule("From", "test2@test.com", "Inbox")
        
        rule_manager.add_rule(rule1, "always")
        rule_manager.add_rule(rule2, "sometimes")
        
        # Get all rules
        all_rules = rule_manager.get_rules()
        assert len(all_rules["always"]) == 1
        assert len(all_rules["sometimes"]) == 1
        
        # Get filtered rules
        always_rules = rule_manager.get_rules("always")
        assert len(always_rules) == 1
        assert always_rules[0] == rule1

    def test_get_rule_by_index(self, rule_manager):
        """Test getting a rule by category and index."""
        rule = EmailRule("From", "test@test.com", "Inbox")
        rule_manager.add_rule(rule, "always")
        
        found_rule = rule_manager.get_rule_by_index("always", 0)
        assert found_rule == rule
        
        # Invalid index
        assert rule_manager.get_rule_by_index("always", 10) is None
        assert rule_manager.get_rule_by_index("nonexistent", 0) is None

    def test_move_rule(self, rule_manager):
        """Test moving a rule between categories."""
        rule = EmailRule("From", "test@test.com", "Inbox")
        rule_manager.add_rule(rule, "sometimes")
        
        result = rule_manager.move_rule(rule, "sometimes", "always")
        assert result is True
        
        assert len(rule_manager.rules["sometimes"]) == 0
        assert len(rule_manager.rules["always"]) == 1
        assert rule_manager.rules["always"][0] == rule

    def test_clear_rules(self, rule_manager):
        """Test clearing rules."""
        rule_manager.add_rule(EmailRule("From", "test@test.com", "Inbox"), "always")
        rule_manager.add_rule(EmailRule("Subject", "Sale", "Promo"), "sometimes")
        
        # Clear specific category
        rule_manager.clear_rules("always")
        assert len(rule_manager.rules["always"]) == 0
        assert len(rule_manager.rules["sometimes"]) == 1
        
        # Clear all
        rule_manager.clear_rules()
        assert len(rule_manager.rules["always"]) == 0
        assert len(rule_manager.rules["sometimes"]) == 0

    def test_display_rules(self, rule_manager, capsys):
        """Test displaying rules."""
        rule_manager.add_rule(EmailRule("From", "test@test.com", "Inbox"), "always")
        rule_manager.display_rules()
        
        captured = capsys.readouterr()
        assert "ALWAYS Rules:" in captured.out
        assert "test@test.com" in captured.out
