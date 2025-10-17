from pathlib import Path
from app import create_app, db
from app.models.prompt import Prompt
from app.extensions import cache
import logging

log = logging.getLogger(__name__)


def run(app=None, prompts_dir: Path = None, create_tables_if_missing: bool = True):
    """Seed prompts from markdown files located in app/seeds/prompts.

    This function is idempotent: it will update existing prompts and create
    missing ones.
    """
    app = app or create_app()
    base = Path(__file__).parent
    prompts_dir = prompts_dir or (base / 'prompts')

    from sqlalchemy import inspect

    with app.app_context():
        # Ensure table exists in dev/test if desired
        if create_tables_if_missing:
            inspector = inspect(db.engine)
            if not inspector.has_table('prompts'):
                db.create_all()

        created = 0
        updated = 0
        if not prompts_dir.exists():
            log.warning('Prompts directory %s does not exist', prompts_dir)
            return {'created': 0, 'updated': 0}

        for p in prompts_dir.glob('*.md'):
            name = p.name
            content = p.read_text(encoding='utf-8')
            existing = Prompt.query.filter_by(name=name).first()
            if existing:
                if existing.content != content:
                    existing.content = content
                    updated += 1
            else:
                db.session.add(Prompt(name=name, content=content))
                created += 1

        db.session.commit()

        # clear cache used by prompt_service
        try:
            cache.delete('all_prompts')
        except Exception:
            pass

        log.info('seed_prompts finished; created=%s updated=%s', created, updated)
        return {'created': created, 'updated': updated}


if __name__ == '__main__':
    res = run()
    print(res)
