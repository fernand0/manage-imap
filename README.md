# Manage IMAP

A command-line tool to manage and organize IMAP mailboxes using a powerful rule-based system. This project is a complete refactoring of an older legacy script into a more robust and maintainable object-oriented application.

## ⚠️ Disclaimer

**This code was migrated from a legacy program. While the main functionality has been refactored, the underlying logic for the rules engine has not been formally tested and should be used with caution.**

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

    The project dependencies are listed in `pyproject.toml`. The recommended way to install them is:

    ```bash
    pip install "google-api-python-client" "oauth2client" "click" "social-modules @ git+https://github.com/fernand0/socialModules.git"
    ```

## Usage

Once the dependencies are installed and the virtual environment is active, run the application with:

```bash
python manage_imap.py
```

You will be presented with a menu to manage your emails and rules.