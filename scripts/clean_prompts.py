#!/usr/bin/env python3
"""
Utility to delete all Prompt rows from the database.

Usage:
  - Dry run (default): python scripts/clean_prompts.py
  - Actually delete: python scripts/clean_prompts.py --yes

This avoids quoting/heredoc issues when running one-liners in PowerShell.
"""

from __future__ import annotations

from app import create_app
from app.extensions import db
from app.models.prompt import Prompt


def main(dry_run: bool = True) -> None:
    app = create_app("default")
    with app.app_context():
        before = Prompt.query.count()
        print(f"Prompts before: {before}")
        if dry_run:
            print("Dry run; no changes made.")
            return
        deleted = db.session.query(Prompt).delete()
        db.session.commit()
        after = Prompt.query.count()
        print(f"Deleted: {deleted}")
        print(f"Prompts after: {after}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Clean Prompt rows from DB")
    parser.add_argument("--yes", "-y", action="store_true", help="Actually delete rows")
    args = parser.parse_args()
    main(dry_run=not args.yes)
