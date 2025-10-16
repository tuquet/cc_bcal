from app.extensions import db, cache
from app.models.prompt import Prompt


@cache.cached(timeout=3600, key_prefix='all_prompts')
def get_all_prompts():
    """
    Get all prompts from the database, sort by file name and cache the results.
    """
    prompts_from_db = Prompt.query.order_by(Prompt.filename).all()
    return {p.filename: p.content for p in prompts_from_db}

