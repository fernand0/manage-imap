"""
Module for managing email organization rules.
"""
import logging
import pickle
from typing import Dict, List, Tuple

class EmailRuleManager:
    """Manages email rules for automated email organization."""
    
    def __init__(self, rules_file: str):
        self.rules_file = rules_file
        self.rules = self._load_rules()
    
    def _load_rules(self) -> Dict[str, List[Tuple]]:
        """Load rules from pickle file."""
        try:
            with open(self.rules_file, 'rb') as f:
                return pickle.load(f)
        except (FileNotFoundError, pickle.PickleError) as e:
            logging.warning(f"Could not load rules: {e}")
            return {'always': [], 'sometimes': []}
    
    def save_rules(self) -> None:
        """Save rules to pickle file."""
        try:
            with open(self.self.rules_file, 'wb') as f:
                pickle.dump(self.rules, f)
            logging.info("Rules saved successfully")
        except Exception as e:
            logging.error(f"Failed to save rules: {e}")
    
    def add_rule(self, rule: Tuple, rule_type: str = 'sometimes') -> None:
        """Add a new rule to the specified category."""
        if rule_type not in self.rules:
            self.rules[rule_type] = []
        
        if rule not in self.rules[rule_type]:
            self.rules[rule_type].append(rule)
            logging.info(f"Added rule to {rule_type}: {rule}")
    
    def remove_rule(self, rule: Tuple, rule_type: str) -> bool:
        """Remove a rule from the specified category."""
        if rule_type in self.rules and rule in self.rules[rule_type]:
            self.rules[rule_type].remove(rule)
            logging.info(f"Removed rule from {rule_type}: {rule}")
            return True
        return False
    
    def display_rules(self) -> None:
        """Display all rules in a formatted way."""
        for category, rules in self.rules.items():
            print(f"\n{category.upper()} Rules:")
            if not rules:
                print("  No rules in this category.")
            for i, rule in enumerate(rules):
                print(f"  {i}: {rule}")
