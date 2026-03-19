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

3.  **Install development dependencies (optional):**

    ```bash
    pip install -e ".[dev]"
    ```

## Usage

Once the dependencies are installed and the virtual environment is active, run the application with:

```bash
python manage_imap.py
```

You will be presented with a menu to manage your emails and rules.

### Command-line Options

```bash
# Run with custom rules file
python manage_imap.py --rules-file /path/to/rules.json

# Migrate legacy pickle rules to JSON format
python manage_imap.py --migrate-only
```

## Features

The main menu provides the following options:

- **Purge deleted mails**: Permanently delete emails marked for deletion in the current folder.
- **Move mail**: Move a selected email to a different folder and optionally create a rule based on it.
- **Change current folder**: Switch to a different IMAP folder.
- **List unread messages**: Display all unread messages in the current folder and offer to mark them as read.
- **Rules Management**: A sub-menu to create, apply, and organize your email filtering rules.
- **Exit**: Quit the application, with an option to save any rule changes.

## Rule Format

Rules are stored in JSON format with the following structure:

```json
{
  "version": "1.0",
  "always": [
    {
      "keyword": "From",
      "pattern": "notifications@github.com",
      "folder": "GitHub"
    }
  ],
  "sometimes": [
    {
      "keyword": "Subject",
      "pattern": "Invoice",
      "folder": "Billing"
    }
  ]
}
```

### Rule Types

- **always**: Rules that are applied automatically without confirmation
- **sometimes**: Rules that require confirmation before applying

### Legacy Format Migration

If you have existing rules in the legacy pickle format (`.dat` file), the application will automatically:

1. Detect the legacy format
2. Create a backup (`.bak` file)
3. Migrate to the new JSON format
4. Save the migrated rules

You can also migrate manually using the `--migrate-only` flag.

## Testing

Run the test suite with:

```bash
pytest tests/ -v
```

## ⚠️ Disclaimer

**This code was migrated from a legacy program. While the main functionality has been refactored and tested, always backup your rules before migration and test thoroughly in your environment.**
