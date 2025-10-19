import json
import os
from typing import Optional

from app.extensions import db
from app.models.script import Script


def run_from_example(app, example_path: str, create_tables_if_missing: bool = False) -> dict:
    """Read a single example JSON file and create or update the Script row.

    The JSON is expected to contain top-level fields matching the Script
    denormalized columns: title, alias, acts (list), characters (list),
    setting (object), builder_configs (object), tone, genre, themes, logline,
    notes.
    """
    if not os.path.isabs(example_path):
        candidate = os.path.join(app.root_path, example_path)
        if os.path.exists(candidate):
            example_path = candidate
        else:
            repo_root = os.path.abspath(os.path.join(app.root_path, '..'))
            candidate = os.path.join(repo_root, example_path)
            if os.path.exists(candidate):
                example_path = candidate

    if not os.path.exists(example_path):
        raise FileNotFoundError(f'Example file not found: {example_path}')

    with app.app_context():
        if create_tables_if_missing:
            db.create_all()

        with open(example_path, 'r', encoding='utf-8') as fh:
            payload = json.load(fh)

        title = payload.get('title')
        alias = payload.get('alias')
        # Minimal requirement: must have alias
        if not alias:
            raise ValueError('Script example must include `alias`')

        # Prepare denormalized string fields (store as JSON text where appropriate)
        acts = json.dumps(payload.get('acts')) if payload.get('acts') is not None else None
        characters = json.dumps(payload.get('characters')) if payload.get('characters') is not None else None
        setting = json.dumps(payload.get('setting')) if payload.get('setting') is not None else None
        builder_configs = json.dumps(payload.get('builder_configs')) if payload.get('builder_configs') is not None else None
        tone = payload.get('tone')
        genre = json.dumps(payload.get('genre')) if payload.get('genre') is not None else None
        themes = json.dumps(payload.get('themes')) if payload.get('themes') is not None else None
        logline = payload.get('logline')
        notes = payload.get('notes')

        created = 0
        updated = 0

        existing = Script.query.filter_by(alias=alias).first()
        if existing:
            changed = False
            # Compare relevant fields and update when changed
            if existing.title != title:
                existing.title = title
                changed = True
            if existing.acts != acts:
                existing.acts = acts
                changed = True
            if existing.characters != characters:
                existing.characters = characters
                changed = True
            if existing.setting != setting:
                existing.setting = setting
                changed = True
            if existing.builder_configs != builder_configs:
                existing.builder_configs = builder_configs
                changed = True
            if existing.tone != tone:
                existing.tone = tone
                changed = True
            if existing.genre != genre:
                existing.genre = genre
                changed = True
            if existing.themes != themes:
                existing.themes = themes
                changed = True
            if existing.logline != logline:
                existing.logline = logline
                changed = True
            if existing.notes != notes:
                existing.notes = notes
                changed = True

            if changed:
                db.session.commit()
                updated = 1
        else:
            s = Script(
                title=title,
                alias=alias,
                acts=acts,
                characters=characters,
                setting=setting,
                builder_configs=builder_configs,
                tone=tone,
                genre=genre,
                themes=themes,
                logline=logline,
                notes=notes,
            )
            db.session.add(s)
            db.session.commit()
            created = 1

    return {"created": created, "updated": updated, "path": example_path}


def run(app, scripts_dir: Optional[str] = None, create_tables_if_missing: bool = False) -> dict:
    """Seed scripts from a directory. Accepts .json script files where the
    content matches the expected script payload. Returns created/updated counts.
    """
    if scripts_dir is None:
        scripts_dir = os.path.join(app.root_path, 'api', 'examples')

    try:
        from pathlib import Path
        if isinstance(scripts_dir, Path):
            scripts_dir = str(scripts_dir)
    except Exception:
        pass

    if not os.path.exists(scripts_dir):
        raise FileNotFoundError(f'Scripts directory not found: {scripts_dir}')

    created = 0
    updated = 0

    with app.app_context():
        if create_tables_if_missing:
            db.create_all()

        for fname in sorted(os.listdir(scripts_dir)):
            full = os.path.join(scripts_dir, fname)
            if not os.path.isfile(full):
                continue
            if not fname.lower().endswith('.json'):
                continue
            try:
                res = run_from_example(app, full, create_tables_if_missing=False)
                created += res.get('created', 0)
                updated += res.get('updated', 0)
            except Exception:
                continue

    return {"created": created, "updated": updated}


if __name__ == '__main__':
    from app import create_app

    app = create_app('default')
    print(run(app, None, create_tables_if_missing=True))
