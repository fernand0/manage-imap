#!/usr/bin/env python3
"""
IMAP Email Management Tool

This module provides functionality to manage IMAP emails with rules-based
organization and automated folder management.
"""

import argparse
import logging
import os
import sys
from typing import List, Tuple, Optional, Any


# Local imports
from socialModules.configMod import DATADIR
from rule_manager import EmailRuleManager, EmailRule


class EmailManager:
    """Main email management class."""

    def __init__(self, rules_file: Optional[str] = None):
        self.api_src: Optional[Any] = None
        self.rules_file = rules_file or f"{DATADIR}/rulesSieve.dat"
        self.rule_manager: Optional[EmailRuleManager] = None
        self._setup_logging()

    def _setup_logging(self) -> None:
        """Configure logging for the application."""
        logging.basicConfig(
            stream=sys.stdout,
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
        )

    def initialize(self) -> None:
        """Initialize the email manager with API and rules."""
        try:
            import socialModules.moduleRules

            rules = socialModules.moduleRules.moduleRules()
            rules.checkRules()

            self.api_src = rules.selectRuleInteractive("imap")
            self.rule_manager = EmailRuleManager(self.rules_file)

        except Exception as e:
            logging.error(f"Failed to initialize: {e}")
            raise

    def reconnect(self) -> None:
        """Re-establish the IMAP session."""
        logging.info("Re-establishing IMAP session...")
        try:
            import socialModules.moduleRules

            rules = socialModules.moduleRules.moduleRules()
            rules.checkRules()
            self.api_src = rules.selectRuleInteractive("imap")
            logging.info("IMAP session re-established successfully.")
        except Exception as e:
            logging.error(f"Failed to re-establish session: {e}")

    def _display_menu_and_get_choice(
        self, menu_title: str, menu_options: List[str]
    ) -> int:
        """Generic helper to display a menu and get a valid choice."""
        while True:
            print("\n" + "=" * 50)
            print(menu_title)
            print("=" * 50)

            for i, option in enumerate(menu_options):
                print(f"{i}: {option}")

            choice = input("\nSelect option: ").strip()

            # Allow 'q' to exit from the main menu, corresponding to option 7
            if menu_title == "MAIN MENU" and choice.lower() == "q":
                return len(menu_options) - 1

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

            if choice == 0:  # Show all rules
                self.rule_manager.display_rules()
            elif choice == 1:  # Create rule from a message
                self.move_message(create_rule=True)
            elif choice == 2:  # Apply a specific rule
                self.apply_one_rule()
            elif choice == 3:  # Apply all 'always' rules
                self.apply_all_rules()
            elif choice == 4:  # Organize rules
                self.organize_rules()
            elif choice == 5:  # Save rules to file
                self.rule_manager.save_rules()
            elif choice == 6:  # Reload rules from file
                self.load_rules()
            elif choice == 7:  # Back to Main Menu
                print("Returning to main menu...")
                break

            input("\nPress Enter to continue...")

    def select_message(self) -> Optional[Any]:
        """Select a message from the current folder."""
        selected_msg = None

        try:
            self.api_src.setPosts()
            posts = self.api_src.getPosts()

            if not posts:
                print(
                    f"No messages found in current folder: {self.api_src.getChannel()}"
                )
            else:
                print("\nRecent messages:")
                for i, msg in enumerate(posts[-15:]):
                    from_addr = self.api_src.getPostFrom(msg)
                    subject = self.api_src.getPostTitle(msg)
                    print(f"{i}: {from_addr} - {subject}")

                while selected_msg is None:
                    try:
                        choice = input(
                            "Select message number (or 'q' to quit): "
                        ).strip()
                        if choice.lower() == "q":
                            break

                        msg_num = int(choice)
                        if 0 <= msg_num < len(posts[-15:]):
                            selected_msg = posts[-(15 - msg_num)]
                        else:
                            print("Invalid message number.")

                    except ValueError:
                        print("Please enter a valid number or 'q'.")

        except Exception as e:
            logging.error(f"Error selecting message: {e}")

        return selected_msg

    def move_message(self, create_rule: bool = False) -> None:
        """Selects a message, moves it to a folder, and optionally creates a rule."""
        try:
            msg = self.select_message()
            if not msg:
                return

            (keyword, textt, textHeader) = self.api_src.selectHeaderAuto(
                self.api_src, msg
            )
            logging.info(f"Rule based on: Header='{keyword}', Content='{textHeader}'")

            textHeaderS = textHeader
            if "Subject" not in keyword and "@" in textHeader:
                domain = textHeader.split("@")[1]
                textHeaderS = next(
                    (part for part in domain.split(".") if part != "www"), textHeaderS
                )

            folder = self.api_src.selectFolderN(
                self.api_src.getClient(), folderM=textHeaderS
            )
            if not folder:
                logging.warning("No folder selected. Aborting.")
                return

            new_rule = (keyword, textHeader, folder)
            self._apply_rule_logic(new_rule, interactive=True)

            if create_rule:
                rule_type = input("Make rule (a)lways or (s)ometimes? ").lower()
                if rule_type == "a":
                    self.rule_manager.add_rule(new_rule, "always")
                elif rule_type == "s":
                    self.rule_manager.add_rule(new_rule, "sometimes")
                else:
                    print("Invalid rule type. Rule not saved.")

        except Exception as e:
            logging.error(f"An error occurred while moving message: {e}", exc_info=True)

    def load_rules(self) -> None:
        """Explicitly re-loads rules from the file."""
        print("Reloading rules...")
        if self.rule_manager:
            self.rule_manager = EmailRuleManager(self.rules_file)
        print("Rules reloaded.")

    def _apply_rule_logic(self, rule: Tuple | EmailRule, interactive: bool) -> None:
        """The core logic for applying a single rule."""
        # Handle both tuple and EmailRule formats
        if isinstance(rule, EmailRule):
            keyword, text_header = rule.keyword, rule.pattern
            folder = rule.folder
        else:
            keyword, text_header, folder = rule

        search_criteria = f'(HEADER {keyword} "{text_header}")'
        logging.info(
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
            print("No messages found matching this rule.")
            return

        msg_list_str = msg_ids[0].decode("utf-8").replace(" ", ",")
        msg_count = len(msg_list_str.split(","))
        print(f"Found {msg_count} messages matching the rule.")

        if interactive:
            if input("Proceed with moving messages? (y/n): ").lower() != "y":
                print("Move operation cancelled.")
                return

        result = self.api_src.moveMails(self.api_src.getClient(), msg_list_str, folder)
        print(f"Move result: {result}")

    def _select_rule(self) -> Optional[Tuple[EmailRule, str]]:
        """Interactively select a rule from the list.
        
        Returns:
            Tuple of (rule, category) or None if no selection.
        """
        self.rule_manager.display_rules()

        categories = list(self.rule_manager.rules.keys())
        if not categories:
            print("No rule categories found.")
            return None

        cat_choice = None
        while True:
            cat_choice = input(
                f"Select category ({'/'.join(categories)}) or 'q' to quit: "
            ).lower()
            if cat_choice == "q":
                return None
            if cat_choice in categories:
                break
            print("Invalid category.")

        if not cat_choice or cat_choice == "q":
            return None

        rules_in_cat = self.rule_manager.rules[cat_choice]
        if not rules_in_cat:
            print(f"No rules in category '{cat_choice}'.")
            return None

        while True:
            try:
                rule_num_str = input(
                    f"Select rule number (0-{len(rules_in_cat)-1}) or 'q' to quit: "
                ).strip()
                if rule_num_str.lower() == "q":
                    return None
                rule_num = int(rule_num_str)
                if 0 <= rule_num < len(rules_in_cat):
                    return (rules_in_cat[rule_num], cat_choice)
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
        print("Applying all 'always' rules...")
        always_rules = self.rule_manager.rules.get("always", [])
        if not always_rules:
            print("No 'always' rules to apply.")
            return

        for rule in always_rules:
            self._apply_rule_logic(rule, interactive=False)
        print("Finished applying all rules.")

    def change_folder(self) -> None:
        """Allows the user to select a different IMAP folder."""
        print("Fetching folder list...")
        try:
            folder = self.api_src.selectFolder(None)
            if folder:
                self.api_src.setChannel(folder)
                logging.info(f"Switched to folder: {self.api_src.getChannel()}")
            else:
                print("No folder selected or folder selection cancelled.")
        except Exception as e:
            logging.error(f"Failed to change folder: {e}", exc_info=True)

    def organize_rules(self) -> None:
        """Move a rule to a different category or delete it."""
        print("\n--- Organize Rules ---")

        result = self._select_rule()
        if not result:
            print("No rule selected.")
            return

        rule_to_move, original_category = result

        if not original_category:
            logging.error(
                "Could not find the selected rule in any category. This should not happen."
            )
            return

        print(f"\nSelected rule: {rule_to_move.keyword}='{rule_to_move.pattern}' -> {rule_to_move.folder} (from '{original_category}')")

        dest_categories = [
            cat for cat in self.rule_manager.rules.keys() if cat != original_category
        ] + ["delete"]
        while True:
            dest_choice = input(
                f"Move to category ({'/'.join(dest_categories)})? "
            ).lower()
            if dest_choice in dest_categories:
                break
            print("Invalid category.")

        if self.rule_manager.remove_rule(rule_to_move, original_category):
            if dest_choice != "delete":
                self.rule_manager.add_rule(rule_to_move, dest_choice)
                print(f"Rule moved from '{original_category}' to '{dest_choice}'.")
            else:
                print("Rule deleted.")
        else:
            logging.error("Failed to remove the rule from its original category.")

    def list_unread_messages(self) -> None:
        """Lists unread messages in the current folder and offers to mark them as read."""
        try:
            self.api_src.setPosts()
            current_folder = self.api_src.getChannel()
            logging.info(f"Searching for unread messages in '{current_folder}'...")

            self.api_src.setChannel(current_folder)

            status, msg_ids = self.api_src.getClient().search(None, '(UNSEEN)')

            if status != 'OK' or not msg_ids[0]:
                print("No unread messages found in this folder.")
                return

            unread_msg_ids = msg_ids[0].decode('utf-8').split()
            print(f"Found {len(unread_msg_ids)} unread messages.")

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
                print(f"{len(unread_msg_ids)} message(s) marked as read.")

        except Exception as e:
            logging.error(f"Failed to list or update unread messages: {e}", exc_info=True)

    def purge_deleted_mails(self) -> None:
        """Permanently delete emails marked for deletion in the current folder."""
        current_folder = self.api_src.getChannel()
        print(
            f"This will permanently delete all emails marked for deletion in the folder '{current_folder}'."
        )

        if input("Are you sure you want to proceed? (y/n): ").lower() != "y":
            print("Purge operation cancelled.")
            return

        try:
            logging.info(f"Expunging messages in folder '{current_folder}'...")
            self.api_src.setPosts()
            typ, data = self.api_src.getClient().expunge()
            if typ == "OK":
                purged_count = len(data) if data and data[0] is not None else 0
                print(
                    f"Successfully purged {purged_count} message(s) from '{current_folder}'."
                )
            else:
                logging.error(
                    f"Failed to expunge folder. Server response: {typ} {data}"
                )
        except Exception as e:
            logging.error(f"An error occurred during expunge: {e}", exc_info=True)


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
    parser.add_argument(
        "--migrate-only",
        action="store_true",
        help="Migrate legacy pickle rules to JSON format and exit",
    )
    args = parser.parse_args()

    rules_file = args.rules_file or f"{DATADIR}/rulesSieve.dat"

    # Handle migrate-only mode
    if args.migrate_only:
        print(f"Migrating rules from: {rules_file}")
        try:
            rule_manager = EmailRuleManager(rules_file, create_backup=True)
            print("Migration completed successfully!")
            print(f"Rules are now stored in JSON format at: {rules_file}")
            if os.path.exists(f"{rules_file}.bak"):
                print(f"Backup created at: {rules_file}.bak")
        except Exception as e:
            print(f"Migration failed: {e}")
            sys.exit(1)
        return

    manager = EmailManager(rules_file=rules_file)
    try:
        manager.initialize()

        while True:
            choice = manager.display_main_menu()

            if choice == 0:  # Purge deleted mails
                manager.purge_deleted_mails()
            elif choice == 1:  # Move mail
                manager.move_message(create_rule=False)
            elif choice == 2:  # Change current folder
                manager.change_folder()
            elif choice == 3:  # List unread messages
                manager.list_unread_messages()
            elif choice == 4:  # Rules Management
                manager._rules_submenu()
            elif choice == 5:  # Reconnect
                manager.reconnect()
            elif choice == 6:  # Exit (ask to save rules)
                if input("Save rules before quitting? (y/n): ").lower() == "y":
                    manager.rule_manager.save_rules()
                print("Exiting.")
                break
            elif choice == 7:  # Exit (discard changes)
                print("Exiting without saving changes.")
                break

            input("\nPress Enter to continue...")

    except Exception as e:
        logging.error(f"Application failed to start: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
