import click
import json
from app.seeds.seed_prompts import run as run_prompts
from app.seeds.seed_scripts import run as run_scripts


def init_seed_commands(app):
    """Register seed-related Flask CLI commands on the given app."""

    @app.cli.command('seed-prompts')
    @click.option('--prompts-dir', default=None, help='Directory containing prompt files or examples')
    @click.option('--create-tables', is_flag=True, default=False, help='Create DB tables if missing')
    @click.option('--out-file', default=None, help='Optional path to write clean JSON output (mapping name->content)')
    def seed_prompts(prompts_dir, create_tables, out_file):
        """Seed prompts from a directory or the packaged examples.

        If `--out-file` is provided, write the legacy mapping (name->content)
        to that file as JSON so callers can consume it without interleaved logs.
        """
        with app.app_context():
            res = run_prompts(app=app, prompts_dir=prompts_dir, create_tables_if_missing=create_tables)
            # Legacy clients expect a mapping name -> content. Print that mapping
            prompts_map = res.get('prompts') if isinstance(res, dict) else None
            if out_file and prompts_map is not None:
                try:
                    with open(out_file, 'w', encoding='utf-8') as fh:
                        json.dump(prompts_map, fh, ensure_ascii=False, indent=2)
                    print(f'Wrote prompts mapping to: {out_file}')
                except Exception as e:
                    print(f'Failed to write out-file: {e}')
            else:
                if prompts_map is not None:
                    print(json.dumps(prompts_map, ensure_ascii=False, indent=2))
                else:
                    print(json.dumps(res, ensure_ascii=False, indent=2))

    @app.cli.command('seed-scripts')
    @click.option('--scripts-dir', default=None, help='Directory containing script JSON examples')
    @click.option('--create-tables', is_flag=True, default=False, help='Create DB tables if missing')
    def seed_scripts(scripts_dir, create_tables):
        """Seed scripts from a directory or the packaged examples."""
        with app.app_context():
            res = run_scripts(app=app, scripts_dir=scripts_dir, create_tables_if_missing=create_tables)
            print(json.dumps(res, ensure_ascii=False, indent=2))
