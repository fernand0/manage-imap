"""
Module for managing email organization rules.

Supports both legacy pickle format and new JSON format with automatic migration.
"""

import json
import logging
import os
import shutil
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any


@dataclass
class EmailRule:
    """Represents a single email filtering rule."""
    keyword: str
    pattern: str
    folder: str

    @classmethod
    def from_tuple(cls, rule_tuple: tuple) -> "EmailRule":
        """Create an EmailRule from a legacy tuple format."""
        return cls(keyword=rule_tuple[0], pattern=rule_tuple[1], folder=rule_tuple[2])

    def to_tuple(self) -> tuple:
        """Convert to legacy tuple format for compatibility."""
        return (self.keyword, self.pattern, self.folder)

    def matches(self, header_value: str) -> bool:
        """Check if this rule matches the given header value."""
        return self.pattern.lower() in header_value.lower()


class EmailRuleManager:
    """Manages email rules for automated email organization."""

    RULES_VERSION = "1.0"

    def __init__(self, rules_file: str, create_backup: bool = True):
        self.rules_file = rules_file
        self.create_backup = create_backup
        self.rules: Dict[str, List[EmailRule]] = {"always": [], "sometimes": []}
        self._load_rules()

    def _load_rules(self) -> None:
        """Load rules from file (JSON or pickle with auto-migration)."""
        if not os.path.exists(self.rules_file):
            logging.info(f"No rules file found at {self.rules_file}, starting with empty rules")
            return

        # Try JSON first (new format)
        try:
            with open(self.rules_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._parse_json_rules(data)
                logging.info("Loaded rules from JSON file")
                return
        except (json.JSONDecodeError, UnicodeDecodeError, KeyError) as e:
            logging.debug(f"Not a valid JSON rules file: {e}, trying pickle format")
            pass  # Not valid JSON, try pickle

        # Fall back to pickle (legacy format)
        self._load_pickle_rules()

    def _parse_json_rules(self, data: Dict[str, Any]) -> None:
        """Parse JSON format rules into EmailRule objects."""
        self.rules = {"always": [], "sometimes": []}
        
        for category in ["always", "sometimes"]:
            if category in data:
                for rule_data in data[category]:
                    if isinstance(rule_data, dict):
                        rule = EmailRule(
                            keyword=rule_data["keyword"],
                            pattern=rule_data["pattern"],
                            folder=rule_data["folder"]
                        )
                        self.rules[category].append(rule)
                    elif isinstance(rule_data, (tuple, list)):
                        # Handle case where JSON has arrays from previous migration
                        rule = EmailRule.from_tuple(tuple(rule_data))
                        self.rules[category].append(rule)

    def _load_pickle_rules(self) -> None:
        """Load rules from legacy pickle format and migrate to JSON."""
        import pickle  # Only import pickle for legacy migration

        try:
            with open(self.rules_file, "rb") as f:
                loaded_rules = pickle.load(f)
            
            logging.warning("Loaded rules from legacy pickle format")
            
            # Create backup before migration
            if self.create_backup:
                backup_path = f"{self.rules_file}.bak"
                shutil.copy2(self.rules_file, backup_path)
                logging.info(f"Created backup of legacy rules at {backup_path}")
            
            # Convert tuple-based rules to EmailRule objects
            self.rules = {"always": [], "sometimes": []}
            for category in ["always", "sometimes"]:
                if category in loaded_rules:
                    for rule_tuple in loaded_rules[category]:
                        if isinstance(rule_tuple, (tuple, list)):
                            rule = EmailRule.from_tuple(tuple(rule_tuple))
                            self.rules[category].append(rule)
            
            # Save as JSON
            self.save_rules()
            logging.info("Rules auto-migrated to JSON format")
            
        except (FileNotFoundError, pickle.PickleError, EOFError) as e:
            logging.warning(f"Could not load rules from pickle: {e}")

    def save_rules(self) -> None:
        """Save rules to JSON file."""
        try:
            data = {
                "version": self.RULES_VERSION,
                "always": [asdict(rule) for rule in self.rules.get("always", [])],
                "sometimes": [asdict(rule) for rule in self.rules.get("sometimes", [])]
            }
            
            with open(self.rules_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            
            logging.info(f"Rules saved to {self.rules_file}")
        except Exception as e:
            logging.error(f"Failed to save rules: {e}")

    def add_rule(self, rule: tuple | EmailRule, rule_type: str = "sometimes") -> None:
        """Add a new rule to the specified category."""
        if rule_type not in self.rules:
            self.rules[rule_type] = []

        # Convert tuple to EmailRule if needed
        if isinstance(rule, tuple):
            rule = EmailRule.from_tuple(rule)

        # Check for duplicates
        if rule not in self.rules[rule_type]:
            self.rules[rule_type].append(rule)
            logging.info(f"Added rule to {rule_type}: {rule.keyword} -> {rule.folder}")

    def remove_rule(self, rule: tuple | EmailRule, rule_type: str) -> bool:
        """Remove a rule from the specified category."""
        # Convert tuple to EmailRule if needed
        if isinstance(rule, tuple):
            rule = EmailRule.from_tuple(rule)

        if rule_type in self.rules and rule in self.rules[rule_type]:
            self.rules[rule_type].remove(rule)
            logging.info(f"Removed rule from {rule_type}: {rule.keyword} -> {rule.folder}")
            return True
        return False

    def get_rules(self, rule_type: Optional[str] = None) -> Dict[str, List[EmailRule]] | List[EmailRule]:
        """Get rules, optionally filtered by type."""
        if rule_type:
            return self.rules.get(rule_type, [])
        return self.rules

    def display_rules(self) -> None:
        """Display all rules in a formatted way."""
        for category, rules in self.rules.items():
            print(f"\n{category.upper()} Rules:")
            if not rules:
                print("  No rules in this category.")
            for i, rule in enumerate(rules):
                print(f"  {i}: {rule.keyword}='{rule.pattern}' -> {rule.folder}")

    def get_rule_by_index(self, category: str, index: int) -> Optional[EmailRule]:
        """Get a rule by category and index."""
        rules = self.rules.get(category, [])
        if 0 <= index < len(rules):
            return rules[index]
        return None

    def move_rule(self, rule: EmailRule, from_category: str, to_category: str) -> bool:
        """Move a rule from one category to another."""
        if self.remove_rule(rule, from_category):
            self.add_rule(rule, to_category)
            return True
        return False

    def clear_rules(self, rule_type: Optional[str] = None) -> None:
        """Clear all rules, or rules of a specific type."""
        if rule_type:
            self.rules[rule_type] = []
            logging.info(f"Cleared all '{rule_type}' rules")
        else:
            self.rules = {"always": [], "sometimes": []}
            logging.info("Cleared all rules")
