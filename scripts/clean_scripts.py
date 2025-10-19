#!/usr/bin/env python3
"""
Utility to delete all Script rows from the database.

Usage:
  - Dry run (default): python scripts/clean_scripts.py
  - Actually delete: python scripts/clean_scripts.py --yes

This avoids quoting/heredoc issues when running one-liners in PowerShell.
"""
from __future__ import annotations

from app import create_app
from app.extensions import db
from app.models.script import Script


def main(dry_run: bool = True) -> None:
    app = create_app("default")
    with app.app_context():
        before = Script.query.count()
        print(f"Scripts before: {before}")
        if dry_run:
            print("Dry run; no changes made.")
            return
        deleted = db.session.query(Script).delete()
        db.session.commit()
        after = Script.query.count()
        print(f"Deleted: {deleted}")
        print(f"Scripts after: {after}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Clean Script rows from DB")
    parser.add_argument("--yes", "-y", action="store_true", help="Actually delete rows")
    args = parser.parse_args()
    main(dry_run=not args.yes)
