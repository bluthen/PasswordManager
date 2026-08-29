# Password Manager

A simple, secure desktop password manager built with Python and PyQt5. Passwords and credentials are stored locally in
GPG-encrypted CSV files (`.gcsv`), organized by customizable categories.

## Prerequisites

- **Python**: 3.13+
- **Package Manager**: [uv](https://github.com/astral-sh/uv)
- **GnuPG**: `gpg` or `gpg2` installed with an existing GPG keypair

## Installation & Running

1. **Install dependencies**:

   ```bash
   uv sync
   ```

2. **Launch the application**:

   ```bash
   uv run python src/main.py
   ```

3. **Run tests**:
   ```bash
   uv run python -m unittest discover tests
   ```

## Initial Setup

Before creating or opening encrypted password files, configure your GPG settings:

1. Open the application and go to **File -> Settings**.
2. Under the **General** tab:
   - **GPG Path**: Enter the path to your GPG binary (e.g., `/usr/bin/gpg2` or `/usr/bin/gpg`), or click `...` to browse
     for it.
   - **GPG Key**: Click `...` to list and select your secret GPG key for encryption/decryption.
   - _(Optional)_ Check **Try to open last saved document on startup** to automatically load your vault.
3. Click **Ok** to save your settings.

## Basic Usage

- **Create/Save a Vault**: Use **File -> Save As...** to create a new `.gcsv` file encrypted with your GPG key.
- **Add Entries**: Click **Entry -> New Entry** to add items with Name, Category, Username, Password, and Comments.
- **Filter by Category**: Use the Category dropdown above the table to view all items or filter by a specific category.
- **Search**: Press `Ctrl+F` or use **View -> Find...** to search through entries.
