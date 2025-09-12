# Manage IMAP

A command-line tool to manage and organize IMAP mailboxes using a powerful rule-based system. This project is a complete refactoring of an older legacy script into a more robust and maintainable object-oriented application.

## Installation

This project uses a virtual environment to manage dependencies.

1.  **Create and activate the virtual environment:**

    ```bash
    # Create the environment
    python3 -m venv .venv

    # Activate it (on Linux/macOS)
    source .venv/bin/activate
    ```

2.  **Install dependencies:**

    The project dependencies are listed in `pyproject.toml`. Install them using pip:

    ```bash
    pip install .
    ```

## Usage

Once the dependencies are installed and the virtual environment is active, run the application with:

```bash
python manage_imap.py
```

You will be presented with a menu to manage your emails and rules.

## Features

The main menu provides the following options:

- **Purge deleted mails**: Permanently delete emails marked for deletion in the current folder.
- **Move mail**: Move a selected email to a different folder and optionally create a rule based on it.
- **Change current folder**: Switch to a different IMAP folder.
- **List unread messages**: Display all unread messages in the current folder and offer to mark them as read.
- **Rules Management**: A sub-menu to create, apply, and organize your email filtering rules.
- **Exit**: Quit the application, with an option to save any rule changes.

## ⚠️ Disclaimer

**This code was migrated from a legacy program. While the main functionality has been refactored, the underlying logic for the rules engine has not been formally tested and should be used with caution.**
