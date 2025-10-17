from pathlib import Path
from app.seeds.seed_prompts import run as run_seed
from app.models.prompt import Prompt
from app import db


def write_prompt(tmp_path: Path, name: str, content: str) -> Path:
    d = tmp_path / 'prompts'
    d.mkdir()
    p = d / name
    p.write_text(content, encoding='utf-8')
    return d


def test_seed_creates_and_idempotent(app, tmp_path):
    with app.app_context():
        prompts_dir = write_prompt(tmp_path, 'a.md', 'A')
        res = run_seed(app=app, prompts_dir=prompts_dir, create_tables_if_missing=True)
        assert res['created'] == 1
        assert Prompt.query.filter_by(name='a.md').first() is not None

        # Run again (idempotent)
        res2 = run_seed(app=app, prompts_dir=prompts_dir, create_tables_if_missing=True)
        assert res2['created'] == 0


def test_seed_updates_existing(app, tmp_path):
    with app.app_context():
        prompts_dir = write_prompt(tmp_path, 'b.md', 'B')
        run_seed(app=app, prompts_dir=prompts_dir, create_tables_if_missing=True)
        p = Prompt.query.filter_by(name='b.md').first()
        assert p.content == 'B'

        # Update file content
        (prompts_dir / 'b.md').write_text('B2', encoding='utf-8')
    res = run_seed(app=app, prompts_dir=prompts_dir, create_tables_if_missing=True)
    assert res['updated'] == 1
    # Ensure session state is refreshed from DB
    db.session.expire_all()
    p = Prompt.query.filter_by(name='b.md').first()
    assert p.content == 'B2'
