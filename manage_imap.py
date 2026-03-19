#!/usr/bin/env python3
"""
IMAP Email Management Tool

This module provides functionality to manage IMAP emails with rules-based
organization and automated folder management.
"""

import argparse
import logging
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
from rule_manager import EmailRuleManager, EmailRule


class EmailManager:
    """Main email management class."""

    def __init__(self, rules_file: Optional[str] = None):
        self.api_src: Optional[Any] = None
        self.rules_file = rules_file or f"{DATADIR}/rulesSieve.dat"
        self.rule_manager: Optional[EmailRuleManager] = None

    def _print_status(self, message: str) -> None:
        """Print a user-facing status message."""
        print(message)

    def initialize(self) -> None:
        """Initialize the email manager with API and rules."""
        try:
            import socialModules.moduleRules

            rules = socialModules.moduleRules.moduleRules()
            rules.checkRules()

            self.api_src = rules.selectRuleInteractive("imap")
            self.rule_manager = EmailRuleManager(self.rules_file)

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
                return MainMenu.EXIT_DISCARD

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
                self.rule_manager.save_rules()
            elif choice == RulesMenu.RELOAD_RULES:
                self.load_rules()
            elif choice == RulesMenu.BACK_TO_MAIN:
                self._print_status("Returning to main menu...")
                break

            input("\nPress Enter to continue...")

    def _display_recent_messages(self, posts: List[Any]) -> None:
        """Display recent messages to the user."""
        self._print_status("\nRecent messages:")
        for i, msg in enumerate(posts[-RECENT_MESSAGES_LIMIT:]):
            from_addr = self.api_src.getPostFrom(msg)
            subject = self.api_src.getPostTitle(msg)
            print(f"{i}: {from_addr} - {subject}")

    def _get_message_choice(self, posts: List[Any]) -> Optional[Any]:
        """Get message selection from user."""
        while True:
            try:
                choice = input(
                    f"Select message number (0-{RECENT_MESSAGES_LIMIT - 1}) or 'q' to quit: "
                ).strip()
                if choice.lower() == "q":
                    return None

                msg_num = int(choice)
                if 0 <= msg_num < len(posts[-RECENT_MESSAGES_LIMIT:]):
                    return posts[-(RECENT_MESSAGES_LIMIT - msg_num)]
                else:
                    print("Invalid message number.")

            except ValueError:
                print("Please enter a valid number or 'q'.")

    def select_message(self) -> Optional[Any]:
        """Select a message from the current folder."""
        try:
            self.api_src.setPosts()
            posts = self.api_src.getPosts()

            if not posts:
                self._print_status(
                    f"No messages found in current folder: {self.api_src.getChannel()}"
                )
                return None

            self._display_recent_messages(posts)
            return self._get_message_choice(posts)

        except Exception as e:
            logger.exception("Error selecting message")

    def _extract_folder_suggestion(self, keyword: str, text_header: str) -> str:
        """Extract a folder suggestion from the header content."""
        if "Subject" not in keyword and "@" in text_header:
            domain = text_header.split("@")[1]
            return next(
                (part for part in domain.split(".") if part != "www"), text_header
            )
        return text_header

    def _get_rule_type_from_user(self) -> Optional[str]:
        """Get rule type (always/sometimes) from user."""
        rule_type = input("Make rule (a)lways or (s)ometimes? ").lower()
        if rule_type == "a":
            return "always"
        elif rule_type == "s":
            return "sometimes"
        return None

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

            folder_suggestion = self._extract_folder_suggestion(keyword, text_header)
            folder = self.api_src.selectFolderN(
                self.api_src.getClient(), folderM=folder_suggestion
            )
            if not folder:
                logger.warning("No folder selected. Aborting.")
                return

            new_rule = (keyword, text_header, folder)
            self._apply_rule_logic(new_rule, interactive=True)

            if create_rule:
                rule_type = self._get_rule_type_from_user()
                if rule_type:
                    self.rule_manager.add_rule(new_rule, rule_type)
                else:
                    self._print_status("Invalid rule type. Rule not saved.")

        except Exception as e:
            logger.exception("An error occurred while moving message")

    def load_rules(self) -> None:
        """Explicitly re-loads rules from the file."""
        self._print_status("Reloading rules...")
        if self.rule_manager:
            self.rule_manager = EmailRuleManager(self.rules_file)
        self._print_status("Rules reloaded.")

    def _apply_rule_logic(self, rule: Tuple | EmailRule, interactive: bool) -> None:
        """The core logic for applying a single rule."""
        # Handle both tuple and EmailRule formats
        if isinstance(rule, EmailRule):
            keyword, text_header = rule.keyword, rule.pattern
            folder = rule.folder
        else:
            keyword, text_header, folder = rule

        search_criteria = f'(HEADER {keyword} "{text_header}")'
        logger.info(
            f"Applying rule: moving messages matching '{search_criteria}' to '{folder}'"
        )

        try:
            self.api_src.setPosts()
            _, msg_ids = self.api_src.getClient().search(None, search_criteria)
        except Exception:
            _, msg_ids = self.api_src.getClient().search(
                "utf-8", search_criteria.encode("utf-8")
            )

        if not msg_ids or not msg_ids[0]:
            self._print_status("No messages found matching this rule.")
            return

        msg_list_str = msg_ids[0].decode("utf-8").replace(" ", ",")
        msg_count = len(msg_list_str.split(","))
        self._print_status(f"Found {msg_count} messages matching the rule.")

        if interactive:
            if input("Proceed with moving messages? (y/n): ").lower() != "y":
                self._print_status("Move operation cancelled.")
                return

        result = self.api_src.moveMails(self.api_src.getClient(), msg_list_str, folder)
        self._print_status(f"Move result: {result}")

    def _select_rule(self) -> Optional[Tuple[EmailRule, str]]:
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
        while True:
            cat_choice = input(
                f"Select category ({'/'.join(categories)}) or 'q' to quit: "
            ).lower()
            if cat_choice == "q":
                return None
            if cat_choice in categories:
                return cat_choice
            print("Invalid category.")

    def _get_rule_index(self, rule_count: int) -> Optional[int]:
        """Get rule index selection from user."""
        while True:
            try:
                rule_num_str = input(
                    f"Select rule number (0-{rule_count - 1}) or 'q' to quit: "
                ).strip()
                if rule_num_str.lower() == "q":
                    return None
                rule_num = int(rule_num_str)
                if 0 <= rule_num < rule_count:
                    return rule_num
                else:
                    print("Invalid rule number.")
            except ValueError:
                print("Please enter a valid number.")

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
        while True:
            dest_choice = input(
                f"Move to category ({'/'.join(dest_categories)})? "
            ).lower()
            if dest_choice in dest_categories:
                return dest_choice
            print("Invalid category.")

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

            if input("\nMark these messages as read? (y/n): ").lower() == 'y':
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

        if input("Are you sure you want to proceed? (y/n): ").lower() != "y":
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

    rules_file = args.rules_file or f"{DATADIR}/rulesSieve.dat"

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
                if input("Save rules before quitting? (y/n): ").lower() == "y":
                    manager.rule_manager.save_rules()
                self._print_status("Exiting.")
                break
            elif choice == MainMenu.EXIT_DISCARD:
                self._print_status("Exiting without saving changes.")
                break

            input("\nPress Enter to continue...")

    except Exception as e:
        logger.exception("Application failed to start")
        sys.exit(1)


if __name__ == "__main__":
    main()
