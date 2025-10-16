from flask import jsonify
from app.models.prompt import Prompt
from app.extensions import db, cache


@cache.cached(timeout=3600, key_prefix='all_prompts')
def get_all_prompts():
    """
    Get all prompts from the database, sort by file name and cache the results.
    """
    prompts_from_db = Prompt.query.order_by(Prompt.name).all()
    return {p.name: p.content for p in prompts_from_db}

def save_prompt(name: str, content: str):
    """
    Creates a new prompt or updates an existing one based on the filename.
    Returns the saved prompt object.
    """
    if not name or not name.endswith('.md'):
        raise ValueError("Name is required and must end with .md")

    prompt = Prompt.query.filter_by(name=name).first()
    if prompt:
        # Update existing prompt
        prompt.content = content
    else:
        # Create new prompt
        prompt = Prompt(name=name, content=content)
        db.session.add(prompt)
    
    db.session.commit()
    cache.delete('all_prompts')
    return prompt

def delete_prompt_by_id(prompt_id: int):
    """Deletes a prompt by its ID."""
    prompt = db.session.get(Prompt, prompt_id)
    if not prompt:
        return jsonify({"error": "Prompt not found"}), 404
    
    db.session.delete(prompt)
    db.session.commit()
    cache.delete('all_prompts')
    return jsonify({"message": "Prompt deleted successfully."})
