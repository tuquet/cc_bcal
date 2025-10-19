#!/usr/bin/env python3
"""
Run both seeders (prompts and scripts) using the app context and write a short summary.

Usage: python scripts/seed_from_examples.py
"""
from __future__ import annotations

from app import create_app
from app.seeds import seed_prompts, seed_scripts


def main():
    app = create_app('default')
    with app.app_context():
        res_p = seed_prompts.run(app, create_tables_if_missing=True)
        res_s = seed_scripts.run(app, create_tables_if_missing=True)
        print(f"prompts created={res_p.get('created')} updated={res_p.get('updated')} total={len(res_p.get('prompts') or {})}")
        print(f"scripts created={res_s.get('created')} updated={res_s.get('updated')}")


if __name__ == '__main__':
    main()
