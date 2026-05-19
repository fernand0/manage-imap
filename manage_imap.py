#!/usr/bin/env python3
"""
IMAP Email Management Tool

This module provides functionality to manage IMAP emails with rules-based
organization and automated folder management.
"""

import argparse
import logging
import re
import sys
from enum import IntEnum
from typing import List, Tuple, Optional, Any

# Constants
MENU_SEPARATOR_WIDTH = 50
RECENT_MESSAGES_LIMIT = 15

# Configure logging at module level
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


class MainMenu(IntEnum):
    """Main menu options."""
    PURGE_DELETED = 0
    MOVE_MAIL = 1
    CHANGE_FOLDER = 2
    LIST_UNREAD = 3
    RULES_MANAGEMENT = 4
    RECONNECT = 5
    EXIT_SAVE = 6
    EXIT_DISCARD = 7


class RulesMenu(IntEnum):
    """Rules management submenu options."""
    SHOW_RULES = 0
    CREATE_RULE = 1
    APPLY_ONE_RULE = 2
    APPLY_ALL_RULES = 3
    ORGANIZE_RULES = 4
    SAVE_RULES = 5
    RELOAD_RULES = 6
    BACK_TO_MAIN = 7


# Local imports
from socialModules.configMod import DATADIR
from socialModules.moduleFilterManager import moduleFilterManager, EmailFilterRule


class EmailManager:
    """Main email management class."""

    def __init__(self, rules_file: Optional[str] = None):
        self.api_src: Optional[Any] = None
        self.rules_file = rules_file or f"{DATADIR}/rulesFilter.json"
        self.rule_manager: Optional[moduleFilterManager] = None

    def _print_status(self, message: str) -> None:
        """Print a user-facing status message."""
        print(message)

    def _get_int_input(
        self,
        prompt: str,
        min_val: int = 0,
        max_val: Optional[int] = None,
        error_msg: str = "Please enter a valid number",
    ) -> Optional[int]:
        """Get integer input from user with range validation.

        Args:
            prompt: The input prompt to display.
            min_val: Minimum allowed value (inclusive).
            max_val: Maximum allowed value (inclusive), or None for no upper limit.
            error_msg: Error message to display for invalid input.

        Returns:
            The validated integer, or None if user entered 'q' to quit.
        """
        user_input = input(prompt).strip()

        # Allow 'q' to quit
        if user_input.lower() == 'q':
            return None

        try:
            value = int(user_input)
            if max_val is not None and not (min_val <= value <= max_val):
                print(f"Please enter a number between {min_val} and {max_val}")
                return -1  # Signal to retry
            if value < min_val:
                print(f"Please enter a number >= {min_val}")
                return -1  # Signal to retry
            return value
        except ValueError:
            print(error_msg)
            return -1  # Signal to retry

    def _check_for_matching_rules(self, header_keyword: str, header_text: str) -> List[EmailFilterRule]:
        """
        Checks if any existing rules match the given header keyword and text.

        Args:
            header_keyword: The keyword of the email header (e.g., "From", "Subject").
            header_text: The content of the email header.

        Returns:
            A list of matching EmailFilterRule objects.
        """
        matching_rules: List[EmailFilterRule] = []
        if not self.rule_manager or not self.rule_manager.rules:
            return matching_rules

        for category in ["always", "sometimes"]:
            for rule in self.rule_manager.rules.get(category, []):
                # Check if keyword matches and pattern matches text_header
                if rule.keyword.lower() == header_keyword.lower() and rule.matches(header_text):
                    matching_rules.append(rule)
        return matching_rules

    def _confirm(self, message: str, default: bool = False) -> bool:
        """Get yes/no confirmation from user.

        Args:
            message: The confirmation message to display.
            default: Default value if user just presses Enter.

        Returns:
            True for yes, False for no.
        """
        suffix = "Y/n" if default else "y/N"
        response = input(f"{message} ({suffix}): ").lower().strip()
        if not response:
            return default
        return response in ("y", "yes")

    def initialize(self) -> None:
        """Initialize the email manager with API and rules."""
        try:
            import socialModules.moduleRules

            rules = socialModules.moduleRules.moduleRules()
            rules.checkRules()

            self.api_src = rules.selectRuleInteractive("imap")

            # Initialize filter manager using socialModules pattern
            self.rule_manager = moduleFilterManager()
            #self.rule_manager.user = "filter_manager"
            self.rule_manager.rules_file = self.rules_file
            print(f"User:    {self.rule_manager.user}")
            self.rule_manager.setApiPosts()  # Load rules

        except Exception as e:
            logger.exception("Failed to initialize")
            raise

    def reconnect(self) -> None:
        """Re-establish the IMAP session."""
        logger.info("Re-establishing IMAP session...")
        try:
            import socialModules.moduleRules

            rules = socialModules.moduleRules.moduleRules()
            rules.checkRules()
            self.api_src = rules.selectRuleInteractive("imap")
            logger.info("IMAP session re-established successfully.")
        except Exception as e:
            logger.exception("Failed to re-establish session")

    def _display_menu_and_get_choice(
        self, menu_title: str, menu_options: List[str]
    ) -> int:
        """Generic helper to display a menu and get a valid choice."""
        while True:
            print("\n" + "=" * MENU_SEPARATOR_WIDTH)
            print(menu_title)
            print("=" * MENU_SEPARATOR_WIDTH)

            for i, option in enumerate(menu_options):
                print(f"{i}: {option}")

            choice = input("\nSelect option: ").strip()

            # Allow 'q' to exit from the main menu
            if menu_title == "MAIN MENU" and choice.lower() == "q":
                choice = str(MainMenu.EXIT_DISCARD)

            try:
                option = int(choice)

                if 0 <= option < len(menu_options):
                    return option
                else:
                    print(f"Please enter a number between 0 and {len(menu_options) - 1}")

            except ValueError:
                print("Please enter a valid number")

    def display_main_menu(self) -> int:
        """Display the main menu and get user selection."""
        menu_options = [
            "Purge deleted mails",
            "Move mail",
            "Change current folder",
            "List unread messages",
            "Rules Management...",
            "Reconnect",
            "Exit (ask to save rules)",
            "Exit",
        ]
        return self._display_menu_and_get_choice("MAIN MENU", menu_options)

    def _rules_submenu(self) -> None:
        """Display and handle the rules management submenu."""
        menu_options = [
            "Show all rules",
            "Create rule from a message",
            "Apply a specific rule",
            "Apply all 'always' rules",
            "Organize rules (move/delete)",
            "Save rules to file",
            "Reload rules from file",
            "Back to Main Menu",
        ]

        while True:
            choice = self._display_menu_and_get_choice("RULES MANAGEMENT", menu_options)

            if choice == RulesMenu.SHOW_RULES:
                self.rule_manager.display_rules()
            elif choice == RulesMenu.CREATE_RULE:
                self.move_message(create_rule=True)
            elif choice == RulesMenu.APPLY_ONE_RULE:
                self.apply_one_rule()
            elif choice == RulesMenu.APPLY_ALL_RULES:
                self.apply_all_rules()
            elif choice == RulesMenu.ORGANIZE_RULES:
                self.organize_rules()
            elif choice == RulesMenu.SAVE_RULES:
                self.rule_manager.updatePosts()
            elif choice == RulesMenu.RELOAD_RULES:
                self.load_rules()
            elif choice == RulesMenu.BACK_TO_MAIN:
                self._print_status("Returning to main menu...")
                break


    def _display_recent_messages(self, posts: List[Any]) -> None:
        """Display recent messages to the user."""
        self._print_status("\nRecent messages:")
        for i, msg in enumerate(posts[-RECENT_MESSAGES_LIMIT:]):
            from_addr = self.api_src.getPostFrom(msg)
            subject = self.api_src.getPostTitle(msg)
            print(f"{i}: {from_addr} - {subject}")

    def _get_message_choice(self, posts: List[Any]) -> Optional[Any]:
        """Get message selection from user."""
        recent_posts = posts[-RECENT_MESSAGES_LIMIT:]
        max_msg = len(recent_posts) - 1
        choice = None
        valid_input = False

        while not valid_input:
            msg_num = self._get_int_input(
                f"Select message number (0-{max_msg}) or 'q' to quit: ",
                min_val=0,
                max_val=max_msg,
                error_msg="Please enter a valid number or 'q'.",
            )
            if msg_num is None:  # User typed 'q'
                choice = None
                valid_input = True
            elif msg_num >= 0:  # Valid number
                choice = recent_posts[msg_num]
                valid_input = True
            # msg_num == -1 means invalid input, loop continues

        return choice

    def select_message(self) -> Optional[Any]:
        """Select a message from the current folder."""
        selected_msg = None
        try:
            self.api_src.setPosts()
            posts = self.api_src.getPosts()

            if not posts:
                self._print_status(
                    f"No messages found in current folder: {self.api_src.getChannel()}"
                )
            else:
                self._display_recent_messages(posts)
                selected_msg = self._get_message_choice(posts)

        except Exception as e:
            logger.exception("Error selecting message")

        return selected_msg

    def _extract_folder_suggestion(self, keyword: str, text_header: str) -> str:
        """Extract a folder suggestion from the header content."""
        suggestion = text_header.strip()

        # If it's a Subject, try to find bracketed content (e.g., [ProjectName])
        if "Subject" in keyword:
            match = re.search(r"\[([^\]]+)\]", suggestion)
            if match:
                suggestion = match.group(1)
        # For other headers, especially those containing email addresses or IDs
        else:
            # Handle "Name <email@domain.com>" or "<id@domain.com>"
            target = suggestion
            if "<" in suggestion and ">" in suggestion:
                target = suggestion.split("<")[1].split(">")[0]

            # If it contains an email address, focus on the domain part
            if "@" in target:
                target = target.split("@")[1]

            # Extract the first meaningful part of the domain/ID
            # (ignoring 'www' and empty parts)
            parts = [
                p.strip()
                for p in target.split(".")
                if p.strip().lower() != "www" and p.strip()
            ]
            if parts:
                suggestion = parts[0]

        return suggestion

    def _get_rule_type_from_user(self) -> Optional[str]:
        """Get rule type (always/sometimes) from user."""
        result = None
        valid_choice = False
        while not valid_choice:
            rule_type = input(
                "Make rule (a)lways or (s)ometimes? (or 'q' to quit): "
            ).lower()
            if rule_type == "q":
                result = None
                valid_choice = True
            elif rule_type == "a":
                result = "always"
                valid_choice = True
            elif rule_type == "s":
                result = "sometimes"
                valid_choice = True
            else:
                print(
                    "Invalid option. Please enter 'a' for always, 's' for sometimes, or 'q' to quit."
                )
        return result

    def move_message(self, create_rule: bool = False) -> None:
        """Selects a message, moves it to a folder, and optionally creates a rule."""
        try:
            msg = self.select_message()
            if not msg:
                return

            (keyword, textt, text_header) = self.api_src.selectHeaderAuto(
                self.api_src, msg
            )
            logger.info(f"Rule based on: Header='{keyword}', Content='{text_header}'")

            # --- New: Check for existing rules and offer to apply ---
            matching_rules = self._check_for_matching_rules(keyword, text_header)
            if matching_rules:
                self._print_status("\nFound existing rules that match this message:")
                for i, rule in enumerate(matching_rules):
                    self._print_status(f"  {i}: Move '{rule.keyword}' matching '{rule.pattern}' to '{rule.folder}'")

                apply_choice = self._get_int_input(
                    f"Enter the number of the rule to apply (0-{len(matching_rules) - 1}), or 'q' to skip: ",
                    min_val=0,
                    max_val=len(matching_rules) - 1,
                    error_msg="Invalid choice. Please enter a number or 'q'."
                )

                if apply_choice is not None and apply_choice != -1:
                    chosen_rule = matching_rules[apply_choice]
                    if self._confirm(f"Apply rule: Move '{chosen_rule.keyword}' matching '{chosen_rule.pattern}' to '{chosen_rule.folder}'?"):
                        self._apply_rule_logic(chosen_rule, interactive=True)
                        return # Exit after applying the chosen rule
                    else:
                        self._print_status("Application of suggested rule cancelled.")
            # --- End New ---

            folder_suggestion = self._extract_folder_suggestion(keyword, text_header)
            folder = self.api_src.selectFolderN(
                self.api_src.getClient(), folderM=folder_suggestion
            )
            if not folder:
                logger.warning("No folder selected. Aborting.")
                return

            # Normalize folder path for rule creation and application
            folder = self._normalize_folder_path(folder)
            new_rule = (keyword, text_header, folder)
            self._apply_rule_logic(new_rule, interactive=True)

            if create_rule:
                rule_type = self._get_rule_type_from_user()
                if rule_type is None:
                    self._print_status("Rule creation cancelled.")
                elif rule_type:
                    self.rule_manager.add_rule(new_rule, rule_type)
                else:
                    self._print_status("Invalid rule type. Rule not saved.")

        except Exception as e:
            logger.exception("An error occurred while moving message")

    def load_rules(self) -> None:
        """Explicitly re-loads rules from the file."""
        self._print_status("Reloading rules...")
        if self.rule_manager:
            self.rule_manager.setApiPosts()  # Reload rules using socialModules pattern
        self._print_status("Rules reloaded.")

    def _construct_search_criteria(self, keyword: str, pattern: str) -> List[str]:
        """Construct valid IMAP search criteria tokens.

        Args:
            keyword: The search key (e.g., 'From', 'Subject', 'BODY')
            pattern: The pattern to match

        Returns:
            A list of strings to be passed as arguments to the IMAP SEARCH command
        """
        keyword_upper = keyword.upper()
        # Escape double quotes and wrap in quotes for IMAP compliance
        safe_pattern = f'"{pattern.replace(chr(34), chr(92) + chr(34))}"'

        # Handle special flags that don't take an argument
        flags = {
            "ALL", "ANSWERED", "DELETED", "DRAFT", "FLAGGED", "NEW",
            "OLD", "RECENT", "SEEN", "UNANSWERED", "UNDELETED",
            "UNDRAFT", "UNFLAGGED", "UNSEEN"
        }
        if keyword_upper in flags:
            return [keyword_upper]

        # Mapping of common header-like keywords to standard IMAP search keys
        # RFC 3501 Section 6.4.4
        standard_keys = {"FROM", "TO", "SUBJECT", "CC", "BCC", "BODY", "TEXT"}
        
        if keyword_upper in standard_keys:
            return [keyword_upper, safe_pattern]

        # Default to HEADER search for anything else
        return ["HEADER", keyword, safe_pattern]

    def _normalize_folder_path(self, folder: str) -> str:
        """Normalize folder path using the IMAP separator."""
        if self.api_src and hasattr(self.api_src, "separator") and self.api_src.separator:
            sep = self.api_src.separator
            # Replace common separators (. and /) with the correct one
            return folder.replace(".", sep).replace("/", sep)
        return folder

    def _apply_rule_logic(self, rule: Tuple | EmailFilterRule, interactive: bool) -> None:
        """The core logic for applying a single rule.

        Args:
            rule: EmailFilterRule instance or tuple of (keyword, pattern, folder)
            interactive: Whether to require user confirmation
        """
        # Handle both tuple and EmailFilterRule formats
        if isinstance(rule, EmailFilterRule):
            keyword, pattern = rule.keyword, rule.pattern
            folder = rule.folder
        else:
            keyword, pattern, folder = rule

        # Normalize folder path using IMAP separator
        folder = self._normalize_folder_path(folder)

        search_tokens = self._construct_search_criteria(keyword, pattern)
        logger.info(
            f"Applying rule: moving messages matching tokens {search_tokens} to '{folder}'"
        )

        try:
            self.api_src.setPosts()
            # Pass tokens as separate arguments. imaplib will handle quoting if necessary 
            # or we can pass the fully formatted string. Most IMAP clients join with spaces.
            status, msg_ids = self.api_src.getClient().search(None, *search_tokens)
            if status != "OK":
                raise ValueError(f"Search failed with status: {status}")
        except Exception as e:
            logger.debug(f"Initial search failed ({e}), retrying with UTF-8...")
            try:
                # Some servers require charset and encoded bytes for non-ASCII
                # When using charset, the search command often expects the query
                # as a single encoded string.
                search_str = " ".join(search_tokens) # Join tokens without adding extra quotes
                status, msg_ids = self.api_src.getClient().search(
                    "utf-8", search_str.encode("utf-8")
                )
            except Exception as e2:
                logger.error(f"Search execution failed: {e2}")
                self._print_status(f"Error searching messages: {e2}")
                return

        if not msg_ids or not msg_ids[0]:
            self._print_status("No messages found matching this rule.")
            return

        msg_list_str = msg_ids[0].decode("utf-8").replace(" ", ",")
        msg_count = len(msg_list_str.split(","))
        self._print_status(f"Found {msg_count} messages matching the rule.")

        if interactive and not self._confirm("Proceed with moving messages"):
            self._print_status("Move operation cancelled.")
            return

        result = self.api_src.moveMails(self.api_src.getClient(), msg_list_str, folder)
        self._print_status(f"Move result: {result}")

    def _select_rule(self) -> Optional[Tuple[EmailFilterRule, str]]:
        """Interactively select a rule from the list.

        Returns:
            Tuple of (rule, category) or None if no selection.
        """
        self.rule_manager.display_rules()

        categories = list(self.rule_manager.rules.keys())
        if not categories:
            self._print_status("No rule categories found.")
            return None

        cat_choice = self._get_category_choice(categories)
        if not cat_choice:
            return None

        rules_in_cat = self.rule_manager.rules[cat_choice]
        if not rules_in_cat:
            self._print_status(f"No rules in category '{cat_choice}'.")
            return None

        rule_index = self._get_rule_index(len(rules_in_cat))
        if rule_index is None:
            return None

        return (rules_in_cat[rule_index], cat_choice)

    def _get_category_choice(self, categories: List[str]) -> Optional[str]:
        """Get category selection from user."""
        cat_choice = None
        while cat_choice is None:
            user_input = input(
                f"Select category ({'/'.join(categories)}) or 'q' to quit: "
            ).lower()
            if user_input == "q":
                return None
            if user_input in categories:
                cat_choice = user_input
            else:
                print("Invalid category.")
        return cat_choice

    def _get_rule_index(self, rule_count: int) -> Optional[int]:
        """Get rule index selection from user."""
        while True:
            result = self._get_int_input(
                f"Select rule number (0-{rule_count - 1}) or 'q' to quit: ",
                min_val=0,
                max_val=rule_count - 1,
                error_msg="Please enter a valid number.",
            )
            if result is None:  # User typed 'q'
                return None
            if result >= 0:  # Valid number
                return result
            # result == -1 means invalid input, loop continues

    def apply_one_rule(self) -> None:
        """Select and apply a single rule interactively."""
        result = self._select_rule()
        if result:
            rule_to_apply, _ = result
            self._apply_rule_logic(rule_to_apply, interactive=True)

    def apply_all_rules(self) -> None:
        """Apply all rules in the 'always' category non-interactively."""
        self._print_status("Applying all 'always' rules...")
        always_rules = self.rule_manager.rules.get("always", [])
        if not always_rules:
            self._print_status("No 'always' rules to apply.")
            return

        for rule in always_rules:
            self._apply_rule_logic(rule, interactive=False)
        self._print_status("Finished applying all rules.")

    def change_folder(self) -> None:
        """Allows the user to select a different IMAP folder."""
        self._print_status("Fetching folder list...")
        try:
            folder = self.api_src.selectFolder(None)
            if folder:
                self.api_src.setChannel(folder)
                logger.info(f"Switched to folder: {self.api_src.getChannel()}")
            else:
                self._print_status("No folder selected or folder selection cancelled.")
        except Exception as e:
            logger.exception("Failed to change folder")

    def _get_destination_category(
        self, original_category: str, available_categories: List[str]
    ) -> Optional[str]:
        """Get destination category from user for rule organization."""
        dest_categories = available_categories + ["delete"]
        dest_choice = None
        while dest_choice is None:
            user_input = input(
                f"Move to category ({'/'.join(dest_categories)})? (or 'q' to quit): "
            ).lower()
            if user_input == "q":
                return None
            if user_input in dest_categories:
                dest_choice = user_input
            else:
                print("Invalid category.")
        return dest_choice

    def organize_rules(self) -> None:
        """Move a rule to a different category or delete it."""
        self._print_status("\n--- Organize Rules ---")

        result = self._select_rule()
        if not result:
            self._print_status("No rule selected.")
            return

        rule_to_move, original_category = result

        if not original_category:
            logger.error(
                "Could not find the selected rule in any category. This should not happen."
            )
            return

        self._print_status(
            f"\nSelected rule: {rule_to_move.keyword}='{rule_to_move.pattern}' -> {rule_to_move.folder} (from '{original_category}')"
        )

        available_categories = [
            cat for cat in self.rule_manager.rules.keys() if cat != original_category
        ]
        dest_choice = self._get_destination_category(original_category, available_categories)

        if dest_choice is None:
            self._print_status("Rule organization cancelled.")
            return

        if self.rule_manager.remove_rule(rule_to_move, original_category):
            if dest_choice != "delete":
                self.rule_manager.add_rule(rule_to_move, dest_choice)
                self._print_status(f"Rule moved from '{original_category}' to '{dest_choice}'.")
            else:
                self._print_status("Rule deleted.")
        else:
            logger.error("Failed to remove the rule from its original category.")

    def list_unread_messages(self) -> None:
        """Lists unread messages in the current folder and offers to mark them as read."""
        try:
            self.api_src.setPosts()
            current_folder = self.api_src.getChannel()
            logger.info(f"Searching for unread messages in '{current_folder}'...")

            self.api_src.setChannel(current_folder)

            status, msg_ids = self.api_src.getClient().search(None, '(UNSEEN)')

            if status != 'OK' or not msg_ids[0]:
                self._print_status("No unread messages found in this folder.")
                return

            unread_msg_ids = msg_ids[0].decode('utf-8').split()
            self._print_status(f"Found {len(unread_msg_ids)} unread messages.")

            for msg_id in unread_msg_ids:
                stat, data = self.api_src.getClient().fetch(
                    msg_id, '(BODY[HEADER.FIELDS (FROM SUBJECT DATE)])'
                )
                if stat == 'OK':
                    header = data[0][1].decode('utf-8')
                    header_lines = [line for line in header.split('\r\n') if line]
                    print(f"- ID: {msg_id}, " + ", ".join(header_lines))

            if self._confirm("Mark these messages as read"):
                for msg_id in unread_msg_ids:
                    self.api_src.getClient().store(msg_id, '+FLAGS', '\\Seen')
                self._print_status(f"{len(unread_msg_ids)} message(s) marked as read.")

        except Exception as e:
            logger.exception("Failed to list or update unread messages")

    def purge_deleted_mails(self) -> None:
        """Permanently delete emails marked for deletion in the current folder."""
        current_folder = self.api_src.getChannel()
        self._print_status(
            f"This will permanently delete all emails marked for deletion in the folder '{current_folder}'."
        )

        if not self._confirm("Are you sure you want to proceed"):
            self._print_status("Purge operation cancelled.")
            return

        try:
            logger.info(f"Expunging messages in folder '{current_folder}'...")
            self.api_src.setPosts()
            typ, data = self.api_src.getClient().expunge()
            if typ == "OK":
                purged_count = len(data) if data and data[0] is not None else 0
                self._print_status(
                    f"Successfully purged {purged_count} message(s) from '{current_folder}'."
                )
            else:
                logger.error(
                    f"Failed to expunge folder. Server response: {typ} {data}"
                )
        except Exception as e:
            logger.exception("An error occurred during expunge")


def main():
    """Main function to run the email manager."""
    parser = argparse.ArgumentParser(
        description="IMAP Email Management Tool with rules-based organization"
    )
    parser.add_argument(
        "--rules-file",
        type=str,
        default=None,
        help="Path to rules file (default: from DATADIR)",
    )
    args = parser.parse_args()

    rules_file = args.rules_file or f"{DATADIR}/rulesFilter.json"

    manager = EmailManager(rules_file=rules_file)
    try:
        manager.initialize()

        while True:
            choice = manager.display_main_menu()

            if choice == MainMenu.PURGE_DELETED:
                manager.purge_deleted_mails()
            elif choice == MainMenu.MOVE_MAIL:
                manager.move_message(create_rule=False)
            elif choice == MainMenu.CHANGE_FOLDER:
                manager.change_folder()
            elif choice == MainMenu.LIST_UNREAD:
                manager.list_unread_messages()
            elif choice == MainMenu.RULES_MANAGEMENT:
                manager._rules_submenu()
            elif choice == MainMenu.RECONNECT:
                manager.reconnect()
            elif choice == MainMenu.EXIT_SAVE:
                if manager._confirm("Save rules before quitting"):
                    manager.rule_manager.updatePosts()
                manager._print_status("Exiting.")
                break
            elif choice == MainMenu.EXIT_DISCARD:
                manager._print_status("Exiting without saving changes.")
                break


    except Exception as e:
        logger.exception("Application failed to start")
        sys.exit(1)


if __name__ == "__main__":
    main()
